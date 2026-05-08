class Calculator:
    """Main class for disambiguate."""

    def __init__(self, a: int, b: int) -> None:
        """
        Initialize the main class with two numbers.

        Args:
        ----
            a (int): The first number.
            b (int): The second number.

        """
        self.a = a
        self.b = b

    def add(self) -> int:
        """
        Add the first and second number.

        Returns
        -------
            int: The sum of the two numbers.

        """
        return self.a + self.b
