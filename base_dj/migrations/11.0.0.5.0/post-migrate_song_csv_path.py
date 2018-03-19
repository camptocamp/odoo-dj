from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__file__)


def migrate(cr, version):
    """Migrate data paths for songs.

    `anthem` now support passing relative paths to `load_csv`.
    Here we drop `data/` from songs paths
    since this bit will come via global ODOO_DATA_PATH.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    updated = False
    for song in env['dj.song'].search([]):
        if song.csv_path.startswith('data/'):
            song.csv_path = song.csv_path[5:]
            updated = True
    if updated:
        _logger.info('Songs csv_path path updated.')
