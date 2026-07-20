# Define the range limits
start_x = 10
end_x = 20
start_y = 12
end_y = 22

# Open a text file to write the output
with open("input/idealized_grid_input.txt", "w") as file:
    # Loop through the columns
    for y in range(start_y, end_y + 1):
        # Loop through the rows
        for x in range(start_x, end_x + 1):
            # Write the row and column to the file
            file.write(f"{x} {y}\n")

print("File 'idealized_grid_input.txt' has been created with the desired output.")