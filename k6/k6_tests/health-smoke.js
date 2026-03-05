import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  vus: Number(__ENV.VUS) || 1000,
  duration: __ENV.DURATION || '10s',
  thresholds: {
    http_req_duration: ['p(95)<300'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/health`, {
    tags: { endpoint: 'health' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'body has status ok': (r) => {
      try {
        const json = r.json();
        return json && json.status === 'ok';
      } catch (_e) {
        return false;
      }
    },
  });

  sleep(1);
}

