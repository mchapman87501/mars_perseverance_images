#!/usr/bin/env python3
"""
image_db manages a database of image metadata.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import datetime
from pathlib import Path
import re
import sqlite3


# Consider supporting schema versioning, migrations, etc.
# This schema may not save all image metadata.
_schema = """
CREATE TABLE IF NOT EXISTS Images (
    image_id TEXT NOT NULL PRIMARY KEY,

    credit TEXT NOT NULL,
    caption TEXT NOT NULL,
    title TEXT NOT NULL,

    cam_instrument TEXT NOT NULL,
    cam_filter TEXT NOT NULL,
    cam_model_component_list TEXT NOT NULL,
    cam_model_type TEXT NOT NULL,
    cam_position TEXT NOT NULL,

    sample_type TEXT NOT NULL,

    full_res_url TEXT,
    json_url TEXT,

    date_taken_utc TIMESTAMP NOT NULL,
    -- date_taken_mars TIMESTAMP NOT NULL,
    -- date_received TIMESTAMP NOT NULL,
    -- sol INTEGER NOT NULL,

    -- misc
    attitude TEXT NOT NULL,
    drive INTEGER,
    site INTEGER,

    -- extended properties:
    ext_mast_azimuth REAL,
    ext_mast_elevation REAL,
    ext_sclk REAL,
    ext_scale_factor REAL,

    -- position?  What coordinates?
    ext_x REAL,
    ext_y REAL,
    ext_z REAL,

    -- subframe rect:
    ext_sf_left REAL,
    ext_sf_top REAL,
    ext_sf_width REAL,
    ext_sf_height REAL,

    -- dimension: (width, height), appears to be image size in pixels
    ext_width REAL,
    ext_height REAL
);
"""


class ImageDB:
    # Database file is created relative to current working dir.
    _default_db_path = Path("mars_perseverance_image_info.db")

    def __init__(self, db_path=None):
        self._db_path = db_path or self._default_db_path

        self._conn = sqlite3.connect(
            str(self._db_path),
            isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cursor = self._conn.cursor()
        cursor.executescript(_schema)
        self._conn.commit()

    def add_or_update(self, json_records):
        """Add or update all images metadata from json_records.

        Args:
            json_records: JSON object constructed from RSS feed's "images"
            value.
        """
        cursor = self._conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        for image_record in json_records:
            self._add_or_update_one(cursor, image_record)
        cursor.execute("COMMIT TRANSACTION")

    def _add_or_update_one(self, cursor, record):
        query = """
        INSERT OR REPLACE INTO Images
        (
            image_id, credit, caption, title,
            cam_instrument, cam_filter, cam_model_component_list,
            cam_model_type, cam_position,
            sample_type,
            full_res_url, json_url,
            date_taken_utc,
            attitude, drive, site,
            ext_mast_azimuth, ext_mast_elevation,
            ext_sclk,
            ext_scale_factor,
            ext_x, ext_y, ext_z,
            ext_sf_left, ext_sf_top, ext_sf_width, ext_sf_height,
            ext_width, ext_height
        ) VALUES (
            :image_id, :credit, :caption, :title,
            :cam_instr, :cam_filter, :cam_comp_list,
            :cam_model_type, :cam_pos,
            :sample_type,
            :image_url, :json_url,
            :date_taken,
            :attitude, :drive, :site,
            :ext_mast_az, :ext_mast_el,
            :ext_sclk,
            :ext_scale_fact,
            :ext_x, :ext_y, :ext_z,
            :ext_sf_l, :ext_sf_t, :ext_sf_w, :ext_sf_h,
            :ext_w, :ext_h
        )
        """

        ext = record["extended"]
        x, y, z = self._opt_float_tuple(ext["xyz"], 3)
        w, h = self._opt_float_tuple(ext["dimension"], 2)
        sf_l, sf_t, sf_w, sf_h = self._opt_int_tuple(ext["subframeRect"], 4)

        values = dict(
            image_id=record["imageid"],
            credit=record["credit"],
            caption=record["caption"],
            title=record["title"],
            cam_instr=record["camera"]["instrument"],
            cam_filter=record["camera"]["filter_name"],
            cam_comp_list=record["camera"]["camera_model_component_list"],
            cam_model_type=record["camera"]["camera_model_type"],
            cam_pos=record["camera"]["camera_position"],
            sample_type=record["sample_type"],
            json_url=record["json_link"],
            image_url=record["image_files"]["full_res"],
            attitude=record["attitude"],
            drive=self._opt_int(record["drive"]),
            site=self._opt_int(record["site"]),
            date_taken=self._timestamp(record["date_taken_utc"]),
            ext_mast_az=self._opt_float(ext["mastAz"]),
            ext_mast_el=self._opt_float(ext["mastEl"]),
            ext_sclk=self._opt_float(ext["sclk"]),
            ext_scale_fact=self._opt_float(ext["scaleFactor"]),
            ext_x=x,
            ext_y=y,
            ext_z=z,
            ext_sf_l=sf_l,
            ext_sf_t=sf_t,
            ext_sf_w=sf_w,
            ext_sf_h=sf_h,
            ext_w=w,
            ext_h=h,
        )

        cursor.execute(query.strip(), values)

    def _timestamp(self, timestamp_str):
        try:
            return datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            return datetime.datetime.strptime(
                timestamp_str, "%Y-%m-%dT%H:%M:%SZ"
            )

    def _opt_val(self, val_str, converter):
        return converter(val_str) if val_str != "UNK" else None

    def _opt_int(self, val_str):
        return self._opt_val(val_str, int)

    def _opt_float(self, val_str):
        return self._opt_val(val_str, float)

    def _opt_tuple(self, val_str, num_fields, converter):
        if val_str == "UNK":
            return tuple([None] * num_fields)
        expr = re.compile(r"^\((.*)\)$")
        if m := expr.match(val_str):
            fields = [converter(f) for f in m.group(1).split(",")]
            if len(fields) == num_fields:
                return tuple(fields)
        return ValueError(f"Invalid {num_fields}-tuple: '{val_str}'")

    def _opt_int_tuple(self, val_str, num_fields):
        return self._opt_tuple(val_str, num_fields, int)

    def _opt_float_tuple(self, val_str, num_fields):
        return self._opt_tuple(val_str, num_fields, float)

    def cursor(self):
        return self._conn.cursor()

    def cameras(self):
        query = "SELECT DISTINCT cam_instrument FROM Images"
        return [row[0] for row in self._conn.cursor().execute(query)]

    def images_for_camera(self, camera, thumbnails=False):
        # Props to SQLAlchemy et al for their way of building queries
        # in code.
        instr_clause = "cam_instrument = ?"
        tn_clause = "sample_type = ?"
        clauses = [c for c in [instr_clause, tn_clause] if c.strip()]
        where_clause = " AND ".join(clauses)
        query = "SELECT * FROM Images WHERE " + where_clause
        sample_type = "Thumbnail" if thumbnails else "Full"
        return self._conn.cursor().execute(query, (camera, sample_type))
