#!/usr/bin/env python3

import threading
import atexit

from time import sleep
from flask import Flask, jsonify, request, Response

from functions import *

addresses = []
networks = []
total_banned = 0

_lock = threading.Lock()
_th = None


def update():
    global addresses, networks, total_banned
    print('Updating info...')
    zi_data = read_zi()
    total_banned, addresses, networks = separate(zi_data)
    print('Finished. Total IPs:', total_banned)


class Updater(threading.Thread):
    def run(self):
        global _lock
        while True:
            with _lock:
                update()
            sleep(120)


def create_app():
    global _th
    app = Flask(__name__)

    def interrupt():
        global _th
        _th.cancel()

    _th = Updater()
    _th.start()

    atexit.register(interrupt)

    return app


if __name__ == '__main__':
    app = create_app()

    @app.route('/banned_count')
    def count():
        if _lock.locked():
            return '', 204

        print_raw = request.args.get('raw', False, bool)

        if print_raw:
            return str(total_banned)
        else:
            return jsonify({
                'total_banned': total_banned
            })

    @app.route('/info')
    def info():
        if _lock.locked():
            return '', 204

        return jsonify({
            'networks': networks,
            'addresses': addresses
        })

    @app.route('/mikrotik')
    def mikrotik():
        global networks, addresses
        if _lock.locked():
            return '', 204

        print_networks = request.args.get('networks', False, bool)
        print_addresses = request.args.get('addresses', False, bool)

        gw = request.args.get('gateway')

        if not ((print_networks or print_addresses) and gw):
            return '', 204

        values = []

        if print_addresses:
            values += addresses

        if print_networks:
            values += networks

        response = Response(mikrotik_format(values, gw))
        response.headers['content-type'] = 'text/plain;charset=UTF-8'

        return response

    app.run(host='0.0.0.0', port=3000, threaded=True)

