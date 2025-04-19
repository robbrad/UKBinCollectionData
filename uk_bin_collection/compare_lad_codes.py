import json
import geopandas as gpd


def extract_lad_codes(input_json_path):
    with open(input_json_path, "r") as f:
        data = json.load(f)

    lad_codes = set()
    lad_code_to_council_input = {}

    for council_key, council_info in data.items():
        if isinstance(council_info, dict):
            if "LAD24CD" in council_info:
                code = council_info["LAD24CD"]
                lad_codes.add(code)
                lad_code_to_council_input[code] = council_key
            if "supported_councils_LAD24CD" in council_info:
                for code in council_info["supported_councils_LAD24CD"]:
                    lad_codes.add(code)
                    lad_code_to_council_input[code] = f"{council_key} (shared)"

    return lad_codes, lad_code_to_council_input


def compare_with_geojson(input_lad_codes, geojson_path):
    gdf = gpd.read_file(geojson_path)
    geojson_lad_codes = set(gdf["LAD24CD"].dropna().unique())

    geojson_lad_map = {
        row["LAD24CD"]: row["LAD24NM"]
        for _, row in gdf.iterrows()
        if "LAD24CD" in row and "LAD24NM" in row
    }

    missing_in_input = geojson_lad_codes - input_lad_codes
    extra_in_input = input_lad_codes - geojson_lad_codes
    matching = input_lad_codes & geojson_lad_codes

    return matching, missing_in_input, extra_in_input, geojson_lad_map


# --- Run the comparison ---
input_json_path = "uk_bin_collection/tests/input.json"
geojson_path = "uk_bin_collection/Local_Authority_Boundaries.geojson"

input_lad_codes, input_name_map = extract_lad_codes(input_json_path)
matching, missing, extra, geojson_name_map = compare_with_geojson(
    input_lad_codes, geojson_path
)

# --- Print results ---
print(f"✅ Matching LAD24CDs ({len(matching)}):")
for code in sorted(matching):
    print(
        f"  {code} → input.json: {input_name_map.get(code)} | geojson: {geojson_name_map.get(code)}"
    )

print(f"\n🟡 LADs in GeoJSON but missing in input.json ({len(missing)}):")
for code in sorted(missing):
    print(f"  {code} → geojson: {geojson_name_map.get(code)}")

print(f"\n🔴 LADs in input.json but not in GeoJSON ({len(extra)}):")
for code in sorted(extra):
    print(f"  {code} → input.json: {input_name_map.get(code)}")
