#!/usr/bin/env python
from enum import Enum
from random import choice
from math import erf


Event = Enum('Event', 'client_arrive client_buy cashier_finish')

def phi(x):
    return (1.0 + erf(x / sqrt(2.0))) / 2.0


class Simulation(object):

    def __init__(self, n, at, ct, bt, mx, log=None):
        assert n >= 2, 'hard requirement'
        assert callable(at)
        assert callable(ct)
        assert callable(bt)
        if log is not None:
            assert callable(log)

        self._gen_arrive_time = at
        self._gen_cashier_time = ct
        self._gen_buy_time = bt
        self._log_fun = log

        self.day = 0
        self.timestamp = 0.0
        self.time_left = 0
        self.days_left = 0
        self.buy_zone = []
        # Note that the first element of the list is not on the actual queue
        self.cashier_queues = tuple([] for _ in range(n))
        self.client_count = 0

        self.next_client = self._gen_arrive_time()
        self._stats = {
            'timestamps': [],
            'queue_sizes': [],
            'buy_zone_sizes': [],
            'client_history': {},
        }

    def _collect_stats(self):
        s = self._stats
        s['timestamps'].append(self.timestamp)
        # XXX: the first client on the list is not actually on the queue
        s['queue_sizes'].append(tuple(max(len(q) - 1, 0) for q in self.cashier_queues))
        s['buy_zone_sizes'].append(len(self.buy_zone))

    def _compute_stats(self):
        from itertools import izip
        from math import sqrt
        s = self._stats

        qd = [h[2] - h[1] for h in s['client_history'].itervalues() if 1 in h and 2 in h]
        s['avg_queue_time'] = aqt = sum(qd) / len(qd)
        s['max_queue_time'] = max(qd)
        s['dev_queue_time'] = sqrt(sum((aqt - d) ** 2 for d in qd) / len(qd))
        # TODO: use inverse of phi function to compute 1.96 value bellow
        # phi(1.96) = 0.975 ==> 95% confidence (*)
        s['confd_rng_queue_time'] = 2 * 1.96 * s['avg_queue_time'] / sqrt(len(qd))

        ts = s['timestamps']
        qs = s['queue_sizes']
        s['avg_queue_size'] = aqs = sum((t1 - t0) * sum(q) / len(q) for q, t0, t1 in izip(qs, ts, ts[1:])) / (ts[-1] - ts[0])
        s['max_queue_size'] = max(q for qq in qs for q in qq)
        s['dev_queue_size'] = sqrt(sum((aqs - q) ** 2 / len(qq) for qq in qs for q in qq) / len(qs))
        s['avg_queue_size_each'] = tuple(sum((t1 - t0) * q for q, t0, t1 in izip(qq, ts, ts[1:])) / (ts[-1] - ts[0]) for qq in izip(*qs))
        s['max_queue_size_each'] = tuple(max(qq) for qq in izip(*qs))
        # 95% confidence range (vide *)
        s['confd_rng_queue_size'] = 2 * 1.96 * s['avg_queue_size'] / sqrt(len(qs))

        td = [h[3] - h[0] for h in s['client_history'].itervalues() if 0 in h and 3 in h]
        s['avg_total_time'] = att = sum(td) / len(td)
        s['max_total_time'] = max(td)
        s['dev_total_time'] = sqrt(sum((att - d) ** 2 for d in td) / len(td))
        # 95% confidence range (vide *)
        s['confd_rng_total_time'] = 2 * 1.96 * s['avg_total_time'] / sqrt(len(td))

        cd = [h[3] - h[2] for h in s['client_history'].itervalues() if 2 in h and 3 in h]
        s['avg_cashr_time'] = act = sum(cd) / len(cd)
        s['max_cashr_time'] = max(cd)
        s['dev_cashr_time'] = sqrt(sum((act - d) ** 2 for d in cd) / len(cd))
        # 95% confidence range (vide *)
        s['confd_rng_cashr_time'] = 2 * 1.96 * s['avg_cashr_time'] / sqrt(len(cd))

    def _log(self, msg):
        if self._log_fun is not None:
            #self._log_fun(self.timestamp, str(self) + ' ' + msg)
            self._log_fun(self.timestamp, msg)

    def _gen_id(self):
        i = self.client_count
        self.client_count = i + 1
        return i

    def _next_event(self):
        """Next event, will return None on some invalid states."""
        infl = [float('inf')]
        cash_lens = [q[0][0] for q in self.cashier_queues if q]
        buys = [c[0] for c in self.buy_zone]
        if self.next_client < min(infl + cash_lens + buys):
            return Event.client_arrive
        elif min(infl + buys) < min(infl + cash_lens):
            return Event.client_buy
        elif min(infl + cash_lens) < infl[0]:
            return Event.cashier_finish

    def _reset_day(self):
        self.time_left = 8 * 60 * 60
        self.days_left -= 1
        self.buy_zone = []
        self.cashier_queues = tuple([] for _ in self.cashier_queues)

    def _advance_time(self, time):
        self.timestamp += time
        self.time_left -= time
        self.next_client -= time
        self.buy_zone = [(t - time, i) for t, i in self.buy_zone]
        self.cashier_queues = [[(t - time, i) for t, i in q] for q in self.cashier_queues]
        if self.time_left <= 0:
            self._reset_day()

    def __str__(self):
        return '{} {}'.format(len(self.buy_zone), tuple(len(q) for q in self.cashier_queues))

    def step(self):
        ev = self._next_event()
        if ev == Event.client_arrive:
            t, i = self.next_client, self._gen_id()
            self._log('client_{} arrived'.format(i))
            self._stats['client_history'][i] = {0: self.timestamp}
            self.buy_zone.append((self._gen_buy_time(), i))
            self.next_client = self._gen_arrive_time()
            self._advance_time(t)
        elif ev == Event.client_buy:
            t, i = min(self.buy_zone)
            self.buy_zone.remove((t, i))
            min_len = min(len(q) for q in self.cashier_queues)
            maybe_queues = [q for q in self.cashier_queues if len(q) == min_len]
            queue = choice(maybe_queues)
            q = self.cashier_queues.index(queue)
            self._stats['client_history'][i][1] = self.timestamp
            if len(queue) == 0:
                self._stats['client_history'][i][2] = self.timestamp
                self._log('client_{} went to cashier_{} (no queue)'.format(i, q))
            else:
                self._log('client_{} went to queue_{}'.format(i, q))
            queue.append((self._gen_cashier_time(), i))
            self._advance_time(t)
        elif ev == Event.cashier_finish:
            (t, i), queue = min((q[0], q) for q in self.cashier_queues if q)
            q = self.cashier_queues.index(queue)
            self._stats['client_history'][i][3] = self.timestamp
            self._log('client_{} left cashier_{}'.format(i, q))
            queue.pop(0)
            if len(queue) > 0:
                k = queue[0][1]
                self._stats['client_history'][k][2] = self.timestamp
                self._log('client_{} went to cashier_{} (from queue)'.format(k, q))
            self._advance_time(t)
        else:
            self._log('invalid event, this is a bug')

        self._collect_stats()

    def simulate(self, days=1):
        self.days_left = days
        self._reset_day()
        #while self.time_left > 0 or self.days_left > 0:
        while self.days_left >= 0:
            self.step()
        self._compute_stats()

    def short_stats(self):
        s = self._stats
        return '\n'.join([
            '',
            'avg queue size: {}'.format(s['avg_queue_size']),
            '95% confd rang: {}'.format(s['confd_rng_queue_size']),
            'max queue size: {}'.format(s['max_queue_size']),
            'dev queue size: {}'.format(s['dev_queue_size']),
            '',
            'avg queue size each: {}'.format(', '.join('%.02f' % s for s in s['avg_queue_size_each'])),
            'max queue size each: {}'.format(', '.join('% 4i' % m for m in s['max_queue_size_each'])),
            '',
            'avg queue time: {}'.format(s['avg_queue_time']),
            '95% confd rang: {}'.format(s['confd_rng_queue_time']),
            'max queue time: {}'.format(s['max_queue_time']),
            'dev queue time: {}'.format(s['dev_queue_time']),
            '',
            'avg total time: {}'.format(s['avg_total_time']),
            '95% confd rang: {}'.format(s['confd_rng_total_time']),
            'max total time: {}'.format(s['max_total_time']),
            'dev total time: {}'.format(s['dev_total_time']),
            '',
            'avg cashr time: {}'.format(s['avg_cashr_time']),
            '95% confd rang: {}'.format(s['confd_rng_cashr_time']),
            'max cashr time: {}'.format(s['max_cashr_time']),
            'dev cashr time: {}'.format(s['dev_cashr_time']),
            '',
        ])


if __name__ == '__main__':
    import sys
    import argparse
    from random import uniform, random
    from math import log

    parser = argparse.ArgumentParser(description='simulation of cashiers')
    parser.add_argument('cashiers', default=4, type=int, help='number of cashiers')
    parser.add_argument('-f', '--client-frequency', default=10.0, type=float, help='frequency of clients per minute')
    parser.add_argument('-d', '--days', default=1, type=int, help='number of days to simulate')
    parser.add_argument('-e', '--export-stats', type=argparse.FileType('w'), help='set the file to export statistics in JSON to')
    parser.add_argument('--log', action='store_true', help='whether we should log the events')
    args = parser.parse_args()

    cashiers_count = args.cashiers
    client_frequency = args.client_frequency
    arrive_time = lambda: 60 * -log(random()) / client_frequency
    cashier_time = lambda: uniform(2 * 60, 6 * 60)
    buy_time = lambda: uniform(30 * 60, 90 * 60)
    lg = args.log and (lambda timestamp, message: sys.stderr.write('{t:09.03f}: {msg}\n'.format(t=timestamp, msg=message))) or None

    s = Simulation(n=cashiers_count, at=arrive_time, ct=cashier_time, bt=buy_time, mx=5, log=lg)
    try:
        print 'Simulating ... ',
        sys.stdout.flush()
        s.simulate(args.days)
        print 'done.'
        print s.short_stats()
        if args.export_stats:
            from json import dump
            dump(s._stats, args.export_stats, indent=2, separators=(',', ': '))
    except KeyboardInterrupt:
        print '\rCancelled.         '
