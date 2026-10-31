"""
GitHub API access and lines-of-code counting.
LOC logic adapted from Andrew6rant/Andrew6rant.

Requires GITHUB_TOKEN for full stats (private repos, contributed repos, LOC).
Without it, only public REST endpoints are used.
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gql(query: str, variables: dict = None) -> dict:
    """POST a GraphQL query to the GitHub API."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "generate.py"}
    if TOKEN:
        headers["Authorization"] = f"bearer {TOKEN}"
    req = urllib.request.Request("https://api.github.com/graphql", data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def rest_get(path: str) -> dict | list:
    """GET from the GitHub REST API."""
    headers = {"User-Agent": "generate.py", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def fetch_stats(username: str, cache_dir: Path) -> dict:
    """
    Returns a dict with total_repos, total_stars, followers, total_commits,
    contributed (e.g. '{Contributed: 25}'), and loc (tuple of total/adds/dels strings).

    With a token, uses GraphQL for complete data and runs the LOC counter.
    Without one, falls back to the public REST API; loc will be None.
    """
    result = {
        "total_repos":   "?",
        "total_stars":   "?",
        "followers":     "?",
        "total_commits": "?",
        "contributed":   "",
        "loc":           None,
    }
 
    try:
        if TOKEN:
            q = """
            query($login: String!) {
              user(login: $login) {
                followers { totalCount }
                repositories(ownerAffiliations: OWNER, first: 1) { totalCount }
              }
            }"""
            u = gql(q, {"login": username})["data"]["user"]
            result["followers"]   = str(u["followers"]["totalCount"])
            result["total_repos"] = str(u["repositories"]["totalCount"])

            # stars across all owned repos
            total_stars, cursor = 0, None
            while True:
                sq = """
                query($login: String!, $cursor: String) {
                  user(login: $login) {
                    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
                      edges { node { stargazers { totalCount } } }
                      pageInfo { endCursor hasNextPage }
                    }
                  }
                }"""
                rpage = gql(sq, {"login": username, "cursor": cursor})["data"]["user"]["repositories"]
                total_stars += sum(e["node"]["stargazers"]["totalCount"] for e in rpage["edges"])
                if not rpage["pageInfo"]["hasNextPage"]:
                    break
                cursor = rpage["pageInfo"]["endCursor"]
            result["total_stars"] = str(total_stars)

            # repos contributed to (owner + collaborator + org member)
            cq = """
            query($login: String!) {
              user(login: $login) {
                repositories(
                  ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER],
                  first: 1
                ) { totalCount }
              }
            }"""
            contrib = gql(cq, {"login": username})["data"]["user"]["repositories"]["totalCount"]
            result["contributed"] = f"{{Contributed: {contrib}}}"

            # LOC -> counts lines written by this user across all repos
            owner_id = _get_owner_id(username)
            loc = _loc_query(username, owner_id, cache_dir)
            # loc = [additions, deletions, net]; format as ("net", "adds++", "dels--")
            result["loc"] = (f"{loc[2]:,}", f"{loc[0]:,}++", f"{loc[1]:,}--")

            # commit count comes from the LOC cache (sums my_commits per repo)
            result["total_commits"] = _commit_counter(username, cache_dir)

        else:
            data = rest_get(f"/users/{username}")
            result["followers"]   = str(data.get("followers", "?"))
            result["total_repos"] = str(data.get("public_repos", "?"))

            total_stars, page = 0, 1
            while True:
                repos = rest_get(f"/users/{username}/repos?per_page=100&page={page}")
                if not repos:
                    break
                total_stars += sum(r.get("stargazers_count", 0) for r in repos)
                if len(repos) < 100:
                    break
                page += 1
            result["total_stars"] = str(total_stars)

            search = rest_get(f"/search/commits?q=author:{username}&per_page=1")
            count  = search.get("total_count", "?")
            result["total_commits"] = f"{count:,}" if isinstance(count, int) else str(count)

    except Exception as e:
        print(f"fetch_stats error: {e}")

    return result


def _get_owner_id(username: str) -> str:
    """Returns the GraphQL node ID for the given user, needed to filter commits by author."""
    res = gql("query($login: String!) { user(login: $login) { id } }", {"login": username})
    return res["data"]["user"]["id"]


def _loc_query(username: str, owner_id: str, cache_dir: Path, cursor=None, edges=None) -> list:
    """
    Fetches all repositories the user has contributed to (as owner, collaborator, or
    org member) and passes them to the cache builder to count lines.
    """
    if edges is None:
        edges = []
    q = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositories(
          first: 60, after: $cursor,
          ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]
        ) {
          edges {
            node {
              nameWithOwner
              defaultBranchRef {
                target { ... on Commit { history { totalCount } } }
              }
            }
          }
          pageInfo { endCursor hasNextPage }
        }
      }
    }"""
    page = gql(q, {"login": username, "cursor": cursor})["data"]["user"]["repositories"]
    edges += page["edges"]
    if page["pageInfo"]["hasNextPage"]:
        return _loc_query(username, owner_id, cache_dir, page["pageInfo"]["endCursor"], edges)
    return _cache_builder(edges, username, owner_id, cache_dir)


def _cache_builder(edges: list, username: str, owner_id: str, cache_dir: Path) -> list:
    """
    Checks each repository against the local cache file. Only recounts LOC when
    the commit count has changed since the last run, then writes the updated cache.
    Returns [additions, deletions, net_lines].
    """
    filename = cache_dir / (hashlib.sha256(username.encode()).hexdigest() + ".txt")
    try:
        data = filename.read_text().splitlines(keepends=True)
    except FileNotFoundError:
        data = []
        filename.write_text("")

    # repo count changed (fork added, repo deleted): reset all cached counts
    if len(data) != len(edges):
        _flush_cache(edges, filename)
        data = filename.read_text().splitlines(keepends=True)

    total = len(edges)
    for i, edge in enumerate(edges):
        node = edge["node"]
        repo_hash, cached_count, *_ = data[i].split()
        try:
            actual_count = (
                node["defaultBranchRef"]["target"]["history"]["totalCount"]
                if node["defaultBranchRef"] else 0
            )
        except (TypeError, KeyError):
            actual_count = 0

        # recount only when the total commit count changed since last run
        if int(cached_count) != actual_count:
            owner, repo_name = node["nameWithOwner"].split("/", 1)
            print(f"  [{i+1}/{total}] counting {node['nameWithOwner']} ({actual_count} commits)...", flush=True)
            try:
                loc = _recursive_loc(owner, repo_name, owner_id)
                data[i] = f"{repo_hash} {actual_count} {loc[2]} {loc[0]} {loc[1]}\n"
            except Exception as e:
                print(f"         skipped: {e}", flush=True)
                data[i] = f"{repo_hash} 0 0 0 0\n"
        else:
            print(f"  [{i+1}/{total}] {node['nameWithOwner']} (cached)", flush=True)

    filename.write_text("".join(data))

    loc_add, loc_del = 0, 0
    for line in data:
        parts = line.split()
        # cache format: repo_hash  commit_count  my_commits  additions  deletions
        loc_add += int(parts[3])
        loc_del += int(parts[4])
    return [loc_add, loc_del, loc_add - loc_del]


def _flush_cache(edges: list, filename: Path):
    """Resets the cache file, e.g. when the repository list changes."""
    with open(filename, "w") as f:
        for edge in edges:
            h = hashlib.sha256(edge["node"]["nameWithOwner"].encode()).hexdigest()
            f.write(f"{h} 0 0 0 0\n")


def _recursive_loc(owner: str, repo: str, owner_id: str, add=0, delete=0, commits=0, cursor=None) -> tuple:
    """
    Pages through a repository's commit history 100 commits at a time.
    Only counts additions and deletions from commits authored by this user.
    """
    q = """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        defaultBranchRef {
          target { ... on Commit {
            history(first: 100, after: $cursor) {
              edges {
                node { ... on Commit {
                  additions deletions
                  author { user { id } }
                } }
              }
              pageInfo { endCursor hasNextPage }
            }
          } }
        }
      }
    }"""
    history = gql(q, {"owner": owner, "repo": repo, "cursor": cursor})
    history = history["data"]["repository"]["defaultBranchRef"]["target"]["history"]
    for edge in history["edges"]:
        node = edge["node"]
        if node["author"]["user"] and node["author"]["user"]["id"] == owner_id:
            commits += 1
            add     += node["additions"]
            delete  += node["deletions"]
    if history["pageInfo"]["hasNextPage"]:
        return _recursive_loc(owner, repo, owner_id, add, delete, commits, history["pageInfo"]["endCursor"])
    return add, delete, commits


def _commit_counter(username: str, cache_dir: Path) -> str:
    """Sums the my_commits field (column 2) across all cached repos."""
    filename = cache_dir / (hashlib.sha256(username.encode()).hexdigest() + ".txt")
    try:
        total = sum(int(line.split()[2]) for line in filename.read_text().splitlines() if line.strip())
        return f"{total:,}"
    except Exception:
        return "?"
