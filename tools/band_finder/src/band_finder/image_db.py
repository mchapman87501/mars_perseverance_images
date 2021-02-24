#!/usr/bin/env python3
"""
image_db manages a database of image metadata.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import sqlite3
from pathlib import Path
import datetime


# Consider supporting schema versioning, migrations, etc.
# This schema may not save all image metadata.
_schema = """
CREATE TABLE IF NOT EXISTS Images (
    image_id TEXT NOT NULL PRIMARY KEY,

    credit TEXT NOT NULL,
    caption TEXT NOT NULL,

    camera_instrument TEXT NOT NULL,
    camera_filter TEXT NOT NULL,
    sample_type TEXT NOT NULL,

    full_res_url TEXT,

    date_taken_utc TIMESTAMP NOT NULL,

    json_link TEXT
);
"""


class ImageDB:
    # Database file is created relative to current working dir.
    _db_path = Path("mars_perseverance_image_info.db")

    def __init__(self):
        self._conn = sqlite3.connect(
            str(self._db_path),
            isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
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
            image_id, credit, caption,
            camera_instrument, camera_filter, sample_type,
            full_res_url, date_taken_utc,
            json_link
        ) VALUES (
            :image_id, :caption, :credit,
            :cam_instr, :cam_filter, :sample_type,
            :image_url, :date_taken, :json_url
        )
        """
        date_taken = datetime.datetime.strptime(
            record["date_taken_utc"],
            "%Y-%m-%dT%H:%M:%SZ"
        )
        values = dict(
            image_id=record["imageid"],
            cam_instr=record["camera"]["instrument"],
            cam_filter=record["camera"]["filter_name"],
            sample_type=record["sample_type"],
            image_url=record["image_files"]["full_res"],
            date_taken=date_taken,
            json_url=record["json_link"],
            caption=record["caption"],
            credit=record["credit"]
        )

        cursor.execute(query.strip(), values)

    def cursor(self):
        return self._conn.cursor()

    def cameras(self):
        query = "SELECT DISTINCT camera_instrument FROM Images"
        return [row[0] for row in self._conn.cursor().execute(query)]

    def images_for_camera(self, camera, thumbnails=False):
        # Props to SQLAlchemy et al for their way of building queries
        # in code.
        instr_clause = "camera_instrument = ?"
        tn_clause = "sample_type = ?"
        clauses = [
            c for c in [instr_clause, tn_clause]
            if c.strip()
        ]
        where_clause = " AND ".join(clauses)
        query = "SELECT * FROM Images WHERE " + where_clause
        sample_type = "Thumbnail" if thumbnails else "Full"
        return self._conn.cursor().execute(query, (camera, sample_type))
