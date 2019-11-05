# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import re
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, '/opt/sites/wjs')

from wjs import create_app
from wjs import settings

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
logger = logging.getLogger(
        "{file_name}-{feature}".format(file_name=os.path.basename(__file__),
                                       feature="add_user"))

SYNC_RPC_LOG_NAME = 'rpc_sun.log'
logger.addHandler(logging.FileHandler(os.path.join(os.path.dirname(__file__), SYNC_RPC_LOG_NAME)))
logger.setLevel(logging.INFO)

NODE_TYPE_REPORT = 2
REPORT_NAME_REGIX = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        from wjs.models import db, WatchedReports, NodesHierarchy, Report

        while True:
            watched_reports = WatchedReports.get_active_watching_reports()

            for wr in watched_reports:
                remote = wr.get_remote_report_file_names()
                storage = wr.get_report_names_in_storage()
                appendable = list(set(remote) - set(storage))
                removable = list(set(storage) - set(remote))

                wr.scp_remote_report_files(wr.path, wr.name, appendable)
                if removable:
                    wr.remove_files(wr.name, removable)

                logging.info('All %s reports need to add to db' % len(appendable))
                for appendable_report in appendable:
                    name = re.findall(REPORT_NAME_REGIX, appendable_report)
                    if name:
                        name = name[0]
                    else:
                        logging.info("Abnormal file name %s" % appendable_report)
                        name = appendable_report

                    node = NodesHierarchy()
                    node.name = name
                    node.parent_id = wr.parent_node_id
                    node.node_type_id = NODE_TYPE_REPORT
                    db.session.add(node)
                    db.session.flush()

                    report = Report(
                        id=node.id,
                        name=name,
                        user_id=wr.owner_id,
                        job_id=None,
                        job_name=None,
                        build_id=None,
                        path=os.path.join(settings.WATCHED_REPORT_DIR, wr.name, appendable_report),
                        parent_node_id=wr.parent_node_id,
                        create_date=datetime.now()
                    )
                    db.session.add(report)
                    logging.info('Success to add one report "%s"' % name)
                logging.info('Reports synchronise complete.')

            db.session.commit()
            time.sleep(3600)
