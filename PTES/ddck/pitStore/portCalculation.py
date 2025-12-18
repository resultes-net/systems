import math

# --- Input Parameters ---
total_volume = 100000  # m3
total_height = 16  # m
theta_degrees = 27  # Degrees
num_nodes = 50  # Node 1 (top) to Node 50 (bottom)
target_volume = total_volume / 2

# Convert degrees to radians
theta_radians = math.radians(theta_degrees)

# --- Step 0: Calculate base radius (r0) ---
k = total_height * math.tan(theta_radians)
a = 3
b = 3 * k
c = (k ** 2) - ((3 * total_volume) / (math.pi * total_height))

discriminant = b ** 2 - (4 * a * c)
r0 = (-b + math.sqrt(discriminant)) / (2 * a)

print(f"--- Basin Geometry ---")
print(f"Calculated Base Radius (r0): {r0:.2f} m")
print(f"Calculated Top Radius: {r0 + k:.2f} m")
print("-" * 30)

# --- Iteration Process (Node 1 is TOP) ---
delta_h = total_height / (num_nodes - 1)

# We use range(1, num_nodes + 1) to match node naming (1 to 50)
for i in range(1, num_nodes + 1):
    # Calculate height from bottom for the volume formula
    # If i=1 (top), current_height_from_bottom = 16
    # If i=50 (bottom), current_height_from_bottom = 0
    current_height_from_bottom = total_height - (i - 1) * delta_h

    # Radius at this specific height
    current_radius = r0 + (current_height_from_bottom * math.tan(theta_radians))

    # Volume from the bottom up to this height
    current_volume = (math.pi * current_height_from_bottom / 3) * (r0 ** 2 + r0 * current_radius + current_radius ** 2)

    # Since we are descending from the top, we look for the first node
    # where the volume is equal to or less than the target.
    if current_volume <= target_volume:
        print(f"--- Results (Descending from Top) ---")
        print(f"Equilibrium reached at Node: {i}")
        print(f"Height from bottom: {current_height_from_bottom:.2f} m")
        print(f"Volume at this level: {current_volume:.2f} m3")
        break