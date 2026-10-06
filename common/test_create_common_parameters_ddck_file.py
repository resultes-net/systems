import pathlib as _pl
import shutil as _su

import create_common_parameters_ddck_file as _ccp
import pandas as _pd
import pytest as _pt
import resultes_pydantic_models.weather_data as _pwd

_ISO_FORMAT = _pwd.WeatherDataFormat.ISO
_TM2_FORMAT = _pwd.WeatherDataFormat.TM2

# Fixed up like uploads (the server's `fix_up_and_validate_tm2_contents`): `pvlib` can't read the
# raw Meteonorm file.
_TM2_FILE_PATH = _ccp.WEATHER_DDCK_DIR_PATH / "CH-Zuerich-Kloten-66700.tm2"


def _write_iso_data(dir_path: _pl.Path, temperatures_degC: list[float]) -> _pl.Path:
    lines = ["# Location: test", "TIME ta Ghoris Gbn w10 EL"]
    lines += [f"{i + 1} {t} 0 0 1 300" for i, t in enumerate(temperatures_degC)]
    file_path = dir_path / _pwd.get_data_file_name(_ISO_FORMAT)
    file_path.write_text("\n".join(lines) + "\n")
    return file_path


def _write_tm2_data(dir_path: _pl.Path) -> _pl.Path:
    file_path = dir_path / _pwd.get_data_file_name(_TM2_FORMAT)
    _su.copy(_TM2_FILE_PATH, file_path)
    return file_path


@_pt.fixture
def ddck_dir_path(tmp_path: _pl.Path) -> _pl.Path:
    dir_path = tmp_path / "weather_ddcks"
    dir_path.mkdir()
    (dir_path / "weather_data_iso.ddck").write_text("iso ddck")
    (dir_path / "weather_data_tm2.ddck").write_text("tm2 ddck")
    return dir_path


@_pt.fixture
def selected_weather_dir_path(tmp_path: _pl.Path) -> _pl.Path:
    dir_path = tmp_path / _pwd.DIR_NAME
    dir_path.mkdir()
    return dir_path


def test_selected_weather_dir_is_below_parameters_dir() -> None:
    assert (
        _ccp.SELECTED_WEATHER_DIR_PATH
        == _ccp.PARAMETERS_DDCK_DIR_PATH / "selected_weather"
    )
    assert _ccp.ROLLED_OUT_WEATHER_DATA_FILE_PATH.name == "data_rolled_out.type99"


def test_get_weather_data_format_iso(selected_weather_dir_path: _pl.Path) -> None:
    _write_iso_data(selected_weather_dir_path, [1.0])
    assert _ccp.get_weather_data_format(selected_weather_dir_path) == _ISO_FORMAT


def test_get_weather_data_format_tm2(selected_weather_dir_path: _pl.Path) -> None:
    (selected_weather_dir_path / _pwd.get_data_file_name(_TM2_FORMAT)).write_text("x")
    # README.md and the like are ignored.
    (selected_weather_dir_path / _pwd.README_FILE_NAME).write_text("readme")
    assert _ccp.get_weather_data_format(selected_weather_dir_path) == _TM2_FORMAT


def test_get_weather_data_format_no_or_two_data_files(
    selected_weather_dir_path: _pl.Path,
) -> None:
    with _pt.raises(ValueError):
        _ccp.get_weather_data_format(selected_weather_dir_path)

    for f in _pwd.WeatherDataFormat:
        (selected_weather_dir_path / _pwd.get_data_file_name(f)).write_text("x")
    with _pt.raises(ValueError):
        _ccp.get_weather_data_format(selected_weather_dir_path)


@_pt.mark.parametrize(
    ("weather_data_format", "expected_contents"),
    [(_ISO_FORMAT, "iso ddck"), (_TM2_FORMAT, "tm2 ddck")],
)
def test_copy_weather_data_ddck(
    tmp_path: _pl.Path,
    ddck_dir_path: _pl.Path,
    weather_data_format: _pwd.WeatherDataFormat,
    expected_contents: str,
) -> None:
    target = tmp_path / "weather_data.ddck"
    _ccp.copy_weather_data_ddck(weather_data_format, ddck_dir_path, target)
    assert target.read_text() == expected_contents


def test_location_parameters_lookup_by_id() -> None:
    p = _ccp.LOCATION_PARAMETERS["alpine"]
    assert (p.longitude, p.std_longitude, p.latitude) == (-9.844, -15, 46.813)
    assert p.utc_offset == 1

    header = _ccp.create_rolled_out_weather_data_file_header("cold")
    assert "<longitude> 113.583" in header
    assert "<gmt> -7.0" in header

    with _pt.raises(ValueError, match="no-such-id"):
        _ccp.create_rolled_out_weather_data_file_header("no-such-id")


def test_location_parameters_cover_shared_iso_weather_data() -> None:
    iso_ids = {p.stem.lower() for p in _ccp.WEATHER_DDCK_DIR_PATH.glob("*.csv")}
    assert iso_ids == set(_ccp.LOCATION_PARAMETERS)


def test_prepare_iso_weather_data(
    tmp_path: _pl.Path,
    selected_weather_dir_path: _pl.Path,
    ddck_dir_path: _pl.Path,
) -> None:
    _write_iso_data(selected_weather_dir_path, [1.0, 2.0, 3.0])
    ddck_file_path = tmp_path / "weather_data.ddck"

    _ccp.prepare_weather_data_and_get_statistics(
        "alpine", selected_weather_dir_path, ddck_dir_path, ddck_file_path
    )

    assert ddck_file_path.read_text() == "iso ddck"

    rolled_out = (selected_weather_dir_path / "data_rolled_out.type99").read_text()
    header, data = rolled_out.split("<data>\n")
    assert header + "<data>\n" == _ccp.create_rolled_out_weather_data_file_header(
        "alpine"
    )
    assert data == "1 1.0 0 0 1 300\n2 2.0 0 0 1 300\n3 3.0 0 0 1 300\n" * 10


def test_iso_statistics(
    tmp_path: _pl.Path,
    selected_weather_dir_path: _pl.Path,
    ddck_dir_path: _pl.Path,
) -> None:
    # January: 0 degC, except for one hour at -10 on day 3 (index 2); February: 10 degC.
    temperatures = [0.0] * 31 * 24 + [10.0] * 28 * 24
    temperatures[2 * 24 + 5] = -10.0
    _write_iso_data(selected_weather_dir_path, temperatures)

    statistics = _ccp.prepare_weather_data_and_get_statistics(
        "alpine", selected_weather_dir_path, ddck_dir_path, tmp_path / "w.ddck"
    )

    assert statistics.first_coldest_day_in_year == 2
    assert statistics.yearly_average_temperature_degC == _pt.approx(
        sum(temperatures) / len(temperatures)
    )
    assert statistics.min_monthly_average_temperature_degC == _pt.approx(-10 / 744)
    assert statistics.max_monthly_average_temperature_degC == _pt.approx(10)


def test_prepare_tm2_weather_data(
    tmp_path: _pl.Path,
    selected_weather_dir_path: _pl.Path,
    ddck_dir_path: _pl.Path,
) -> None:
    _write_tm2_data(selected_weather_dir_path)
    ddck_file_path = tmp_path / "weather_data.ddck"

    statistics = _ccp.prepare_weather_data_and_get_statistics(
        "5e0a17c3d2", selected_weather_dir_path, ddck_dir_path, ddck_file_path
    )

    assert ddck_file_path.read_text() == "tm2 ddck"
    # No roll-out (and no location parameters needed) for TM2.
    assert not (selected_weather_dir_path / "data_rolled_out.type99").exists()

    # Zurich-Kloten: roughly 9 degC yearly average, coldest in winter, warmest in summer.
    assert 7 < statistics.yearly_average_temperature_degC < 11
    # January 12th, the day with the lowest hourly temperature (-11.7 degC).
    assert statistics.first_coldest_day_in_year == 11
    assert statistics.min_monthly_average_temperature_degC < 3
    assert statistics.max_monthly_average_temperature_degC > 16
    assert 6 < statistics.temperature_amplitude_degC < 12


def test_tm2_first_coldest_day_in_leap_year(
    tmp_path: _pl.Path,
    selected_weather_dir_path: _pl.Path,
    ddck_dir_path: _pl.Path,
) -> None:
    # `pvlib` dates all values with the year of the first data line, so a typical year whose
    # January is from a leap year would have no February 29th.
    data_file_path = _write_tm2_data(selected_weather_dir_path)
    with data_file_path.open(newline="") as file:
        header_line, *data_lines = file.read().splitlines(keepends=True)

    def fix_up(data_line: str) -> str:
        data_line = data_line[:1] + "96" + data_line[3:]
        if data_line[3:9] == "122501":  # December 25th, first hour.
            data_line = data_line[:67] + "-500" + data_line[71:]  # Dry bulb: -50 degC.
        return data_line

    data_file_path.write_text(
        header_line + "".join(fix_up(l) for l in data_lines), newline=""
    )

    statistics = _ccp.prepare_weather_data_and_get_statistics(
        "zurich", selected_weather_dir_path, ddck_dir_path, tmp_path / "w.ddck"
    )

    assert statistics.first_coldest_day_in_year == 358


@_pt.mark.parametrize(
    ("coldest_hour_index", "expected_day"),
    [(0, 0), (23, 0), (24, 1), (8759, 364)],
)
def test_first_coldest_day_in_year(coldest_hour_index: int, expected_day: int) -> None:
    # Type 77's time shift: 0 for January 1st, 364 for December 31st.
    temperatures = [0.0] * 8760
    temperatures[coldest_hour_index] = -10.0

    statistics = _ccp._create_weather_data_statistics(_pd.Series(temperatures))

    assert statistics.first_coldest_day_in_year == expected_day


@_pt.mark.parametrize(
    ("coldest_time_h", "expected_day"),
    [(1, 0), (24, 0), (25, 1), (8760, 364)],
)
def test_iso_first_coldest_day_in_year(
    tmp_path: _pl.Path,
    selected_weather_dir_path: _pl.Path,
    ddck_dir_path: _pl.Path,
    coldest_time_h: int,
    expected_day: int,
) -> None:
    # `TIME` is the end of the hour: `TIME` 24 is the last hour of January 1st.
    temperatures = [0.0] * 8760
    temperatures[coldest_time_h - 1] = -10.0
    _write_iso_data(selected_weather_dir_path, temperatures)

    statistics = _ccp.prepare_weather_data_and_get_statistics(
        "alpine", selected_weather_dir_path, ddck_dir_path, tmp_path / "w.ddck"
    )

    assert statistics.first_coldest_day_in_year == expected_day
