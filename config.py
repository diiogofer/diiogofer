import datetime as dt

USER     = "diiogofer"
HOST     = "github"
BIRTHDAY = dt.date(2005, 8, 16)
WIDTH    = 60  # max characters per info line

INFO = [
    ("OS",     "Windows 11, Ubuntu, Kali Linux"),
    ("Uptime", "{uptime}"),
    ("Host",   "KTH Royal Institute of Technology"),
    ("Kernel", "Paranoia-Driven Development"),
    ("IDE",    "VSCode"),
    None,
    ("Languages.Programming", "Python, Java, C, C++, SQL, gRPC"),
    ("Languages.Real",        "Português, English, Español, Svenska"),
    None,
    ("Hobbies.Software", "Building security tools, CTFs"),
    ("Hobbies.Hardware", "Arduino, Hardware Hacking"),
]

CONTACT = [
    ("Email.Personal", "diogo.sendim.fernandes@gmail.com"),
    ("LinkedIn",       "diogo-t-s-f"),
    ("GitHub",         USER),
]

GITHUB_STATS = [
    ("Repos", "{total_repos} {contributed} | Stars: {total_stars}"),
    ("Commits", "{total_commits} | Followers: {followers}"),
    ("Lines of Code on GitHub", "{lines_of_code}"),
]

THEMES = {
    "dark_mode.svg":  dict(
        bg="#161b22", text="#c9d1d9", key="#ffa657",
        value="#a5d6ff", cc="#616e7f", add="#3fb950", rem="#f85149",
    ),
    "light_mode.svg": dict(
        bg="#f6f8fa", text="#24292f", key="#953800",
        value="#0a3069", cc="#8c959f", add="#1a7f37", rem="#cf222e",
    ),
}
