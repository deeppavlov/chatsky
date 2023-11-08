from colorama import init, Fore, Style


_CURRENT_VERSION = "0.6.0"
_VERSION_FILES = ["scripts/misc.py", "docs/source/conf.py", "dff/__init__.py", "pyproject.toml"]


def info():
    init()
    print(f"\nThanks for your interest in {Fore.YELLOW}Dialog Flow Framework{Style.RESET_ALL}!\n")
    print(f"{Fore.BLUE}poetry install --all-extras{Style.RESET_ALL}: Install development-ready version of framework")
    print(f"{Fore.BLUE}poetry env remove --all{Style.RESET_ALL}: Remove all virtual environments\n")
    print(f"{Fore.BLUE}poetry run help{Style.RESET_ALL}: Display this message again")
    print(f"{Fore.BLUE}poetry run lint{Style.RESET_ALL}: Run linters")
    print(f"{Fore.BLUE}poetry run format{Style.RESET_ALL}: Run formatters")
    print(
        f"{Fore.BLUE}poetry run test_no_cov{Style.RESET_ALL}:"
        + " Run tests without coverage, skipping all tests for unavailable services,"
        + " this is the most complete testing without Docker"
    )
    print(
        f"{Fore.BLUE}poetry run test_no_deps{Style.RESET_ALL}:"
        + " Run tests without any dependencies, allowing skipping everything"
    )
    print(
        f"{Fore.BLUE}poetry run test_all{Style.RESET_ALL}:"
        + " Run ALL tests, prohibit skipping, run Docker (slow, closest to CI)"
    )
    print(
        f"{Fore.BLUE}poetry run docs{Style.RESET_ALL}:"
        + " Build Sphinx docs; activate your virtual environment before execution"
    )
    print(
        f"{Fore.BLUE}poetry run pre_commit{Style.RESET_ALL}:" + " Register a git hook to lint the code on each commit"
    )
    print(
        f"{Fore.BLUE}poetry run version_patch{Style.RESET_ALL}:"
        + " Increment patch number in metadata files"
        + f" ({Fore.RED}9.9.1{Style.RESET_ALL} -> {Fore.GREEN}9.9.2{Style.RESET_ALL})"
    )
    print(
        f"{Fore.BLUE}poetry run version_minor{Style.RESET_ALL}:"
        + " Increment version minor in metadata files"
        + f" ({Fore.RED}9.1.1{Style.RESET_ALL} -> {Fore.GREEN}9.2.0{Style.RESET_ALL})"
    )
    print(
        f"{Fore.BLUE}poetry run version_major{Style.RESET_ALL}:"
        + " Increment version major in metadata files"
        + f" ({Fore.RED}8.8.1{Style.RESET_ALL} -> {Fore.GREEN}9.0.0{Style.RESET_ALL})"
    )
    print(f"{Fore.BLUE}poetry run clean_docs{Style.RESET_ALL}:" + " Remove all documentation build roots")
    print(f"{Fore.BLUE}poetry run clean{Style.RESET_ALL}:" + " Clean all build artifacts\n")
