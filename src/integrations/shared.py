import os


SUPPORTED_SOURCE_CONTROL_PROVIDERS = ["GitHub", "GitLab"]

text_extensions = [".txt", ".md", ".rtf"]
python_extensions = [".py", ".pyw", ".pyc", ".pyo"]
javascript_extensions = [".js", ".mjs"]
java_extensions = [".java", ".class", ".jar"]
csharp_extensions = [".cs"]
cplusplus_extensions = [".cpp", ".cxx", ".cc", ".h", ".hpp"]
php_extensions = [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"]
swift_extensions = [".swift"]
typescript_extensions = [".ts"]
ruby_extensions = [".rb", ".erb"]
go_extensions = [".go"]
kotlin_extensions = [".kt", ".kts"]
rust_extensions = [".rs"]
scala_extensions = [".scala"]
dart_extensions = [".dart"]
perl_extensions = [".pl", ".pm"]
haskell_extensions = [".hs", ".lhs"]
lua_extensions = [".lua"]
objective_c_extensions = [".m", ".mm"]
elixir_extensions = [".ex", ".exs"]
clojure_extensions = [".clj", ".cljs", ".cljc", ".edn"]

other_files = [
    ".html",
    ".css",
    ".c",
    ".sh",
    ".bat",
    ".scala",
    ".groovy",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".rst",
    ".tex",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".log",
    ".sql",
    ".r",
    ".ps1",
    ".tmpl",
    ".tpl",
    ".template",
]

# Combine all the extensions
TEXT_BASED_EXTENSIONS = (
    text_extensions
    + python_extensions
    + javascript_extensions
    + java_extensions
    + csharp_extensions
    + cplusplus_extensions
    + php_extensions
    + swift_extensions
    + typescript_extensions
    + ruby_extensions
    + go_extensions
    + kotlin_extensions
    + rust_extensions
    + scala_extensions
    + dart_extensions
    + perl_extensions
    + haskell_extensions
    + lua_extensions
    + objective_c_extensions
    + elixir_extensions
    + clojure_extensions
    + other_files
)


# Heuristic to determine if a file is text-based (requires me to download the entire file first)
def is_text_based_content(content: bytes) -> bool:
    # Check if the content has any null bytes
    if b"\x00" in content:
        return False
    # Optionally, check for a high percentage of printable characters
    printable_threshold = 0.9
    num_printable = sum(
        c.isprintable() or c.isspace() for c in content.decode("ascii", "ignore")
    )
    return (num_printable / len(content)) > printable_threshold


# Extension-based heuristic to determine if a file is text-based (does not require a download)
def is_text_based_extension(file_path: str):
    # Extract the file extension and check if it's in our set of text-based extensions
    _, extension = os.path.splitext(file_path)

    return extension.strip() == "" or extension.lower() in TEXT_BASED_EXTENSIONS
