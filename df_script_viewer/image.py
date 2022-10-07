def create_image(plot: bytes, output_file: str):
    with open(output_file, "wb") as file:
        file.write(plot)
