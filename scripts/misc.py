from colorama import init, Fore, Style


def info():
    init()
    print(f"\nThanks for your interest in {Fore.YELLOW}Dialog Flow Framework{Style.RESET_ALL}!\n")
    print(
        f"{Fore.BLUE}poetry install --with lint,test,devel,tutorials,docs --all-extras{Style.RESET_ALL}:"
        + "Install development-ready version of framework"
    )
    print(f"{Fore.BLUE}poetry env remove --all{Style.RESET_ALL}: Remove all virtual environments\n")
    print(f"{Fore.BLUE}poetry run info{Style.RESET_ALL}: Display this message again")
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
    print(f"{Fore.BLUE}poetry run clean_docs{Style.RESET_ALL}: Remove all documentation build roots")
    print(f"{Fore.BLUE}poetry run clean{Style.RESET_ALL}: Clean all build artifacts\n")
