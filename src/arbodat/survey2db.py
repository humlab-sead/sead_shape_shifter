import csv
import psycopg
from psycopg import sql
from pathlib import Path


def sanitise_column_name(name: str) -> str:
    """
    Turn a CSV header into a safe SQL identifier.
    Adjust as needed for your conventions.
    """
    name = name.strip()
    name = name.lower()
    # Replace spaces and forbidden chars with underscore
    for ch in " -.;:/\\()[]{}!?\"'#%&*+,":
        name = name.replace(ch, "_")
    # Collapse multiple underscores
    while "__" in name:
        name = name.replace("__", "_")
    # Strip leading/trailing underscores
    name = name.strip("_")
    if not name:
        name = "col"
    return name


def uniquify_column_names(header: list[str]) -> list[str]:
    """
    Ensure all column names are unique by appending _1, _2, etc. to duplicates.
    Modifies the header list in place and also returns it.
    """
    seen = {}
    for i, col in enumerate(header):
        if col in seen:
            seen[col] += 1
            header[i] = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
    return header


NAME_MAP: dict[str, str] = {
    "ProjektNr": "project_number",
    "Befu": "feature_number",
    "ProbNr": "sample_number",
    "PCODE": "sample_code",
    "BNam": "species",
    "Name D": "name_de",
    "Name_E": "name_en",
    "Name_F": "name_fr",
    "Name_I": "name_it",
    "cf": "cf_indicator",
    "RTyp": "remain_type",
    "RTypGrup": "remain_type_group",
    "Zust": "preservation_abbrev",
    "Zustand": "preservation_description",
    "SumFAnzahl": "find_count",
    "SumFGewicht": "find_weight",
    "geschätzt": "is_estimated_count",
    "SumFFrag": "fragment_count",
    "SumPflR": "plant_remain_count",
    "Anmerkung": "species_note",
    "EDatProb": "sampling_date",
    "Strat": "stratigraphy",
    "Schi": "layer",
    "Quadr": "square",
    "Plan": "plan_number",
    "TiefeVon": "depth_from",
    "TiefeBis": "depth_to",
    "Prob_üNN": "elevation_asl_sample",
    "KoordX": "coord_x",
    "KoordY": "coord_y",
    "KoordZ": "coord_z",
    "AblaBdgProb": "is_sample_dry_wet",
    "ChronoDat": "chronological_date",
    "ChronoDat Beschreibung": "chronological_date_description",
    "Vorfu": "is_mass_find",
    "ArchDat": "archeaologic_period",
    "ArchDat_Beschreibung": "archaeological_period_description",
    "Epoche": "epoch",
    "Epochen_Beschreibung": "epoch_description",
    "KultGr": "cultural_group",
    "ProbTyp": "sample_type",
    "ProbTyp Beschreibung": "sample_type_description",
    "Expr1042": "sample_volume",
    "ORG2,0": "organic_2mm",
    "ORG1,0": "organic_1mm",
    "ORG0,5": "organic_0_25mm",
    "ORG0,25": "organic_0_5mm",
    "MIN2,0": "mineral_2mm",
    "MIN1,0": "mineral_1mm",
    "MIN0,5": "mineral_0_25mm",
    "MIN0,25": "mineral_0_5mm",
    "SedProb": "is_subsample_",
    "FlSchn": "flotation_channel",
    "BefuTyp": "feature_type",
    "GrJahrBefu": "construction_year_feature",
    "FustelTyp": "site_type",
    "Fundstellentyp_Beschreibung": "site_type_description",
    "OFustelTyp": "upper_site_type",
    "OFustelTyp Beschreibung": "upper_site_type_description",
    "FustelTyp?": "is_uncertain_site_type",
    "Gebäude": "building",
    "okBefu": "feature_ok",
    "okErh": "preservation_ok",
    "BotBest": "botanical_identification",
    "BestJa": "botanical_identification_year",
    "Fustel": "site_name",
    "Ort": "place",
    "Kreis": "district",
    "Land": "county",
    "Staat": "country",
    "FlurStr": "place_street",
    "EVNr": "site_reference_number",
    "NaturE": "natural_region",
    "NaturrEinh": "natural_region_unit",
    "NaturHaupteinheit": "natural_major_unit",
    "TK": "map_sheet",
    "Koordinatensystem": "coordinate_system",
    "Easting": "easting",
    "Northing": "northing",
    "Höhe": "elevation",
    "ArchAusg": "archaeological_excavator",
    "ArchBear": "archaeological_analyst",
    "Limes": "limes_indicator",
    "BotBear": "botanical_analyst",
    "Aut": "author",
    "PJahr": "publication_year",
    "okFustel": "is_site_ok",
    "Familie": "family",
    "S_Od": "system_order",
    "TaxAut": "taxon_author",
    "Achtung": "warning",
    "L_u": "light_requirement_uncertain",
    "L": "light_requirement",
    "T_u": "temperature_requirement_uncertain",
    "T": "temperature_requirement",
    "K_u": "continentality_uncertain",
    "K": "continentality",
    "F_u": "moisture_uncertain",
    "F": "moisture",
    "F_s": "moisture_special",
    "Re_u": "reaction_uncertain",
    "Re": "reaction",
    "N_u": "nutrients_uncertain",
    "N": "nutrients",
    "S_u": "salt_tolerance_uncertain",
    "S": "salt_tolerance",
    "SMet": "heavy_metal_tolerance",
    "Leb": "life_form",
    "Bl_u": "flowering_time_uncertain",
    "Bl": "flowering_time",
    "G_u": "growth_form_uncertain",
    "G": "growth_form",
    "Kl_u": "vegetation_class_uncertain",
    "Kl": "vegetation_class",
    "O_u": "vegetation_order_uncertain",
    "O": "vegetation_order",
    "V_u": "association_uncertain",
    "V": "association",
    "U_u": "subassociation_uncertain",
    "U": "subassociation",
    "Soz_u": "sociological_group_uncertain",
    "Soz": "sociological_group",
    "Ökogruppe_u": "ecological_group_uncertain",
    "Dom_u": "species_dominance",
    "Dom": "species_dominance_uncertainty",
    "WUA": "weed_indicator",
    "WUE": "weed_indicator_extended",
    "BLA": "leaf_type",
    "BLE": "leaf_habit",
    "ARE": "aridity",
    "Zeig": "indicator_value",
    "Pio": "pioneer",
    "Roh": "ruderal",
    "WT": "water_tolerance",
    "SozGrup": "sociological_group_extended",
    "Anm": "annotation",
    "Ge": "medicinal",
    "Hü": "luxury",
    "Öl": "oil_plant",
    "Kp": "crop_plant",
    "Imp": "imported",
    "Med": "medical_use",
    "Ess": "edible",
    "Gar": "garden_plant",
    "Nut": "useful",
    "M": "male",
    "W": "female",
    "FW": "woody_plant",
    "TKG": "thousand_kernel_weight",
    "ProjektNr": "project_number",
    "Befu": "feature_number",
    "ProbNr": "sample_number",
    "PCODE": "sample_code",
    "BNam": "species",
    "Name D": "name_de",
    "Name_E": "name_en",
    "Name_F": "name_fr",
    "Name_I": "name_it",
    "cf": "cf_indicator",
    "RTyp": "remain_type",
    "RTypGrup": "remain_type_group",
    "Zust": "preservation_abbrev",
    "Zustand": "preservation_description",
    "SumFAnzahl": "find_count",
    "SumFGewicht": "find_weight",
    "geschätzt": "is_estimated_count",
    "SumFFrag": "fragment_count",
    "SumPflR": "plant_remain_count",
    "Anmerkung": "species_note",
    "EDatProb": "sampling_date",
    "Strat": "stratigraphy",
    "Schi": "layer",
    "Quadr": "square",
    "Plan": "plan_number",
    "TiefeVon": "depth_from",
    "TiefeBis": "depth_to",
    "Prob_üNN": "elevation_asl_sample",
    "KoordX": "coord_x",
    "KoordY": "coord_y",
    "KoordZ": "coord_z",
    "AblaBdgProb": "is_sample_dry_wet",
    "ChronoDat": "chronological_date",
    "ChronoDat Beschreibung": "chronological_date_description",
    "Vorfu": "is_mass_find",
    "ArchDat": "archeaologic_period",
    "ArchDat_Beschreibung": "archaeological_period_description",
    "Epoche": "epoch",
    "Epochen_Beschreibung": "epoch_description",
    "KultGr": "cultural_group",
    "ProbTyp": "sample_type",
    "ProbTyp Beschreibung": "sample_type_description",
    "Expr1042": "sample_volume",
    "ORG2,0": "organic_2mm",
    "ORG1,0": "organic_1mm",
    "ORG0,5": "organic_0_25mm",
    "ORG0,25": "organic_0_5mm",
    "MIN2,0": "mineral_2mm",
    "MIN1,0": "mineral_1mm",
    "MIN0,5": "mineral_0_25mm",
    "MIN0,25": "mineral_0_5mm",
    "SedProb": "is_subsample_",
    "FlSchn": "flotation_channel",
    "BefuTyp": "feature_type",
    "GrJahrBefu": "construction_year_feature",
    "FustelTyp": "site_type",
    "Fundstellentyp_Beschreibung": "site_type_description",
    "OFustelTyp": "upper_site_type",
    "OFustelTyp Beschreibung": "upper_site_type_description",
    "FustelTyp?": "is_uncertain_site_type",
    "Gebäude": "building",
    "okBefu": "feature_ok",
    "okErh": "preservation_ok",
    "BotBest": "botanical_identification",
    "BestJa": "botanical_identification_year",
    "Fustel": "site_name",
    "Ort": "place",
    "Kreis": "district",
    "Land": "county",
    "Staat": "country",
    "FlurStr": "place_street",
    "EVNr": "site_reference_number",
    "NaturE": "natural_region",
    "NaturrEinh": "natural_region_unit",
    "NaturHaupteinheit": "natural_major_unit",
    "TK": "map_sheet",
    "Koordinatensystem": "coordinate_system",
    "Easting": "easting",
    "Northing": "northing",
    "Höhe": "elevation",
    "ArchAusg": "archaeological_excavator",
    "ArchBear": "archaeological_analyst",
    "Limes": "limes_indicator",
    "BotBear": "botanical_analyst",
    "Aut": "author",
    "PJahr": "publication_year",
    "okFustel": "is_site_ok",
    "Familie": "family",
    "S_Od": "system_order",
    "TaxAut": "taxon_author",
    "Achtung": "warning",
    "L_u": "light_requirement_uncertain",
    "L": "light_requirement",
    "T_u": "temperature_requirement_uncertain",
    "T": "temperature_requirement",
    "K_u": "continentality_uncertain",
    "K": "continentality",
    "F_u": "moisture_uncertain",
    "F": "moisture",
    "F_s": "moisture_special",
    "Re_u": "reaction_uncertain",
    "Re": "reaction",
    "N_u": "nutrients_uncertain",
    "N": "nutrients",
    "S_u": "salt_tolerance_uncertain",
    "S": "salt_tolerance",
    "SMet": "heavy_metal_tolerance",
    "Leb": "life_form",
    "Bl_u": "flowering_time_uncertain",
    "Bl": "flowering_time",
    "G_u": "growth_form_uncertain",
    "G": "growth_form",
    "Kl_u": "vegetation_class_uncertain",
    "Kl": "vegetation_class",
    "O_u": "vegetation_order_uncertain",
    "O": "vegetation_order",
    "V_u": "association_uncertain",
    "V": "association",
    "U_u": "subassociation_uncertain",
    "U": "subassociation",
    "Soz_u": "sociological_group_uncertain",
    "Soz": "sociological_group",
    "Ökogruppe": "ecological_group",
    "Ökogruppe_u": "ecological_group_uncertain",
    "Dom_u": "species_dominance",
    "Dom": "species_dominance_uncertainty",
    "WUA": "weed_indicator",
    "WUE": "weed_indicator_extended",
    "BLA": "leaf_type",
    "BLE": "leaf_habit",
    "ARE": "aridity",
    "Zeig": "indicator_value",
    "Pio": "pioneer",
    "Roh": "ruderal",
    "WT": "water_tolerance",
    "SozGrup": "sociological_group_extended",
    "Anm": "annotation",
    "Ge": "medicinal",
    "Hü": "luxury",
    "Öl": "oil_plant",
    "Kp": "crop_plant",
    "Imp": "imported",
    "Med": "medical_use",
    "Ess": "edible",
    "Gar": "garden_plant",
    "Nut": "useful",
    "M": "male",
    "W": "female",
    "FW": "woody_plant",
    "TKG": "thousand_kernel_weight",
    "SOURCE": "source"
}


def upload_csv_to_new_table(
    csv_filename: str,
    dsn: str,
    table_name: str,
    schema: str | None = None,
):
    """
    Create a new table and upload CSV into it using psycopg3 COPY.

    - All columns are created as TEXT.
    - Uses the first row of the CSV as header.
    """

    csv_path: Path = Path(csv_filename)

    # 1) Read header from CSV
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header: list[str] = next(reader)  # first line
        # rename duplicate column names

    if not header:
        raise ValueError("CSV file has no header row")

    raw_cols: list[str] = header

    if any(col not in NAME_MAP for col in raw_cols):
        missing = [col for col in raw_cols if col not in NAME_MAP]
        raise ValueError(f"Unmapped column names in CSV: {missing}")
    cols: list[str] = [NAME_MAP[col] for col in raw_cols]
    # cols: list[str] = [sanitise_column_name(c) for c in raw_cols]
    # cols = uniquify_column_names(cols)

    # 2) Build fully qualified table identifier
    if schema:
        table_ident = sql.Identifier(schema, table_name)
    else:
        table_ident = sql.Identifier(table_name)

    # 3) Connect and create table
    with psycopg.connect(dsn) as conn:
        conn.execute("SET client_encoding TO 'UTF8';")  # optional but safe

        col_defs = [sql.SQL("{} TEXT").format(sql.Identifier(col_name)) for col_name in cols]
        create_stmt = sql.SQL("CREATE TABLE {} ({});").format(
            table_ident,
            sql.SQL(", ").join(col_defs),
        )

        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {};").format(table_ident))

            cur.execute(create_stmt)
            conn.commit()  # commit table creation before COPY

        # 4) COPY data from CSV into the new table
        with conn.cursor() as cur:
            copy_sql = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ';')").format(
                table_ident,
                sql.SQL(", ").join(sql.Identifier(c) for c in cols),
            )

            with cur.copy(copy_sql) as copy:
                with csv_path.open("r", encoding="utf-8") as f:
                    # Stream file in chunks to avoid loading entire file into memory
                    for chunk in iter(lambda: f.read(1024 * 1024), ""):
                        if not chunk:
                            break
                        copy.write(chunk)

        conn.commit()


if __name__ == "__main__":
    dsn = "postgresql://humlab_admin@humlabseadserv.srv.its.umu.se:5433/sead_staging"
    upload_csv_to_new_table(
        csv_filename="data/arbodat_mal_elena_input.csv",
        dsn=dsn,
        table_name="arbodat_mal_elena_input",
        schema="public",  # or None
    )
