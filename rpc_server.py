# -*- coding: utf-8 -*-
import os
import sys
import errno
import logging
import subprocess
from datetime import datetime


logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
logger = logging.getLogger(
        "{file_name}-{feature}".format(file_name=os.path.basename(__file__),
                                       feature="add_user"))

logger.addHandler(logging.FileHandler("/home/lars/logger_rpc_sun.log"))
logger.setLevel(logging.INFO)


from optparse import OptionParser

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SocketServer import ThreadingMixIn

WJS_SERVER = 'moon'
WJS_BEING_WATCHED_FILE_PATH = '/home/jenkins/ci-report/_being_watched_reports'
WJS_LOG_PATH = 'jenkins@%s:{}' % WJS_SERVER


# daemonize tool ######################################################################
def basic_daemonize():
    # See http://www.erlenstar.demon.co.uk/unix/faq_toc.html#TOC16
    if os.fork():   # launch child and...
        os._exit(0) # kill off parent
    os.setsid()
    if os.fork():   # launch child and...
        os._exit(0) # kill off parent again.
    os.umask(022)   # Don't allow others to write
    null = os.open('/dev/null', os.O_RDWR)
    for i in range(3):
        try:
            os.dup2(null, i)
        except OSError, e:
            if e.errno != errno.EBADF:
                raise
    os.close(null)


def writePID(pidfile):
    open(pidfile, 'wb').write(str(os.getpid()))
    if not os.path.exists(pidfile):
        raise Exception("pidfile %s does not exist" % pidfile)


def checkPID(pidfile):
    if not pidfile:
        return
    if os.path.exists(pidfile):
        try:
            pid = int(open(pidfile).read())
        except ValueError:
            sys.exit('Pidfile %s contains non-numeric value' % pidfile)
        try:
            os.kill(pid, 0)
        except OSError, why:
            if why[0] == errno.ESRCH:
                # The pid doesnt exists.
                print('Removing stale pidfile %s' % pidfile)
                os.remove(pidfile)
            else:
                sys.exit("Can't check status of PID %s from pidfile %s: %s" %
                         (pid, pidfile, why[1]))
        else:
            sys.exit("Another server is running, PID %s\n" % pid)


def daemonize(pidfile):
    checkPID(pidfile)
    basic_daemonize()
    writePID(pidfile)


def demote(user_uid, user_gid):
    def result():
        os.setgid(user_gid)
        os.setuid(user_uid)
    return result


# rpc registered functions ######################################################################

def list_dir(path):
    try:
        return os.listdir(path)
    except OSError as e:
        return []


def copy_files(source_dir, target_dir, file_names):
    print("copy_files")
    # WJS_LOG_PATH = 'jenkins@%s:{}' % WJS_SERVER 

    print("Copy all %s files to wjs log server" % len(file_names))
    for name in file_names:
        source_file = os.path.join(source_dir, name)
        target_file = os.path.join(target_dir, name)
        p = subprocess.Popen(['sshpass', '-p', 'jenkins123', 'scp', source_file, WJS_LOG_PATH.format(target_file)], stdout=subprocess.PIPE)
        print(p.communicate())
    return True


class AsyncXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-p', '--port', dest='port', help='Listening port for RPC. Default is 8060.')
    parser.add_option('-d', '--debug', dest='debug', help='Debug model', default=False, action='store_true')

    (options, args) = parser.parse_args()

    if options.port:
        listening_port = options.port
        if not listening_port.isdigit():
            logging.error('The port must be pure numbers')
            sys.exit(0)
    else:
        listening_port = 8060

    if not options.debug:
        daemonize('/tmp/%s.pid' % os.path.basename(__file__)[:-3])

    server = AsyncXMLRPCServer(('0.0.0.0', int(listening_port)))
    logging.info('Listening on port %s...' % listening_port)

    server.register_function(list_dir, 'list_dir')
    server.register_function(copy_files, 'copy_files')

    server.serve_forever()
