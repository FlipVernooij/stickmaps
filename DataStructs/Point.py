class PointStruct:

    def __init__(
            self,
            depth: int,
            azimut_in: int = 0,
            azimut_out: int = 0,
            length_in: int = 0,
            length_out: int = 0,
            temp: int = None
    ):
        self.depth = depth
        self.azimut_in = azimut_in
        self.azimut_out = azimut_out
        self.length_in = length_in
        self.length_out = length_out
        self.temp = temp