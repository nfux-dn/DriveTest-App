"""Demo test: intentional script error (spec section 47).

Raises an exception before writing a result so the runner classifies this as
SCRIPT_ERROR, demonstrating that execution failures are kept separate from
product/test failures (spec section 8).
"""


def main() -> None:
    print("script_error: about to fail intentionally")
    raise RuntimeError("Intentional failure to demonstrate SCRIPT_ERROR classification.")


if __name__ == "__main__":
    main()
