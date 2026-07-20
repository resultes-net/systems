import math as _mt

import matplotlib.pyplot as _plt
import pandas as _pd
import os as _os


class BoreHoleField:
    def __init__(self):
        self.rectangular = self.Rectangular()
        self.circular = self.Circular()

    class Rectangular:

        def area_and_distance(self, length: float, width: float, distance: float):
            """
            :param length: length of the area
            :param width: width of the area
            :param distance: distance between boreholes
            :return: nx = amount of boreholes in the x-axis, ny = amount of boreholes in the y-axis,
                    distance = distance of boreholes, area = total area of boreholefield
            """
            if length % distance != 0:
                raise ValueError("Length must be divisible by the distance without a remainder!")
            if width % distance != 0:
                raise ValueError("Width must be divisible by the distance without a remainder!")

            area = length * width # (m2)
            nx = int(length / distance - 1)
            ny = int(width / distance - 1)
            return nx, ny, distance, area


        def amount_and_distance(self, amount: int, distance: float):
            """
            :param amount: total number of boreholes in boreholefield
            :param distance: distance between boreholes
            :return: nx = amount of boreholes in the x-axis, ny = amount of boreholes in the y-axis,
                    distance = distance of boreholes, area = total area of boreholefield
            """
            nx = int(round(_mt.sqrt(amount)))
            ny = amount / nx
            while not ny.is_integer():
                nx += 1
                ny = amount / nx

            ny = int(ny)
            area = (nx+2)*distance * (ny+2)*distance
            return nx, ny, distance, area


    class Circular:

        def radius_and_distance(self, radius: float, distance: float):
            """
            :param radius: outer radius of the circular boreholefield
            :param distance: distance between the boreholes
            :return: amount = amount of boreholes, n_list = list of amount of boreholes per circular perimeter,
                    distance = distance of boreholes, area = total area of boreholefield
            """
            if radius % distance !=0:
                raise ValueError("Radius must be divisible by the distance without a remainder!")

            area = round(radius**2 * _mt.pi, 3) # (m2)
            num_rings = int((radius-distance) / distance ) # amount of rings, the radius is for the outer boundary, that's why a distance is subtracted from the nr
            amount = 1   # it starts with 1 because there is always 1 borehole in the middle of the circle
            n_list = [1]

            for i in range(1, num_rings):
                circumference = i * 2 * distance * _mt.pi
                n = _mt.floor(circumference / distance)
                n_list.append(n)
                amount += n

            return amount, n_list, distance, area

        def amount_and_distance(self, approx_amount: int, distance: float):
            """
            :param approx_amount: approximate amount of boreholes for the corresponding ring
            :param distance: distance between the boreholes and each ring
            :return: real_amount = exact amount of boreholes, n_list = list of amount of boreholes per ring,
                    distance = distance of boreholes, area = total area of boreholefield
            """
            i = 1
            n_list = [1]
            remaining_amount = approx_amount - 1
            approx_amount -= 1

            while remaining_amount > 0:
                circumference = i * distance * 2 * _mt.pi
                n = _mt.floor(circumference / distance)
                n_list.append(n)
                i += 1
                remaining_amount -= n

            real_amount = approx_amount - remaining_amount
            area = round((i*distance)**2 * _mt.pi,3)
            return real_amount, n_list, distance, area


class calc_coordinates:
    @staticmethod
    def rectangular(nx: int, ny: int, distance: float):
        """
        :param nx: amount of boreholes in the x-axis
        :param ny: amount of boreholes in the y-axis
        :param distance: distance between boreholes
        :return: none
        """
        x_list = [i * distance for i in range(nx) for _ in range(ny)]
        y_list = [j * distance for _ in range(nx) for j in range(ny)]

        matrix = f"{nx}x{ny}"
        ntot = nx*ny
        list_to_csv(x_list, y_list, matrix, distance, ntot)
        plot_coordinates(x_list, y_list)

    @staticmethod
    def circular(n: int, n_list: list, distance: float):
        """
        :param n: amount of boreholes
        :param n_list: list of amount of boreholes per ring
        :param distance: distance between boreholes
        :return: none
        """
        x_list = []
        y_list = []
        for i, count in enumerate(n_list):
            for j in range(count):
                angle = 2 * _mt.pi * j / count
                x = round(_mt.cos(angle)*distance*i,3)
                y = round(_mt.sin(angle)*distance*i,3)
                x_list.append(x)
                y_list.append(y)

        matrix = f"R{len(n_list)*distance}_N{n}"
        list_to_csv(x_list, y_list, matrix, distance, n)
        plot_coordinates(x_list, y_list)


def list_to_csv(x_list, y_list, matrix, distance, ntot):
        folder_name = "txt_files"
        file_name = matrix + f"_{distance}m.txt"

        _os.makedirs(folder_name, exist_ok=True)
        file_path = _os.path.join(folder_name, file_name)

        df = _pd.DataFrame({'x' : x_list, 'y' : y_list})
        coordinates = df.to_csv(sep='\t', index=False, header=False, lineterminator='\n')
        header = matrix+f";\tborehole field\n{distance}\n{ntot}\n"
        with open(file_path, 'w') as f:
            f.write(header + coordinates)


def plot_coordinates(x_list, y_list):
    _plt.scatter(x_list, y_list)
    _plt.xlabel("x values [m]")
    _plt.ylabel("y values [m]")
    _plt.title("borehole coordinates")
    _plt.show()


def run_circular():
    bhf = BoreHoleField()
    cc = calc_coordinates()

    n, n_list, distance, *_ = bhf.circular.amount_and_distance(approx_amount=50,distance=8)
    # n, n_list, distance, area,*_ = bhf.circular.radius_and_distance(radius=30, distance=3)
    print(n, n_list, distance)
    cc.circular(n,n_list,distance)


def run_rectangular():
    bhf = BoreHoleField()
    cc = calc_coordinates()

    nx, ny, distance,*_ = bhf.rectangular.amount_and_distance(amount=2 ,distance=3)
    # nx, ny, distance,*_ = bhf.rectangular.area_and_distance(length=100, width=100, distance=5)
    print(nx,ny,distance)
    cc.rectangular(nx, ny, distance)


if __name__ == '__main__':
    run_rectangular()
    # run_circular()