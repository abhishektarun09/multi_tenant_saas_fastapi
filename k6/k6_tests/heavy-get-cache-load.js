import http from 'k6/http';
import { check, group, sleep } from 'k6';

// Base URL defaults to Render deployment; override with BASE_URL env if needed
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Authentication: pass your JWT via JWT_TOKEN env variable
const JWT_TOKEN = __ENV.JWT_TOKEN || '';

// Project ID for list-members endpoint (set via env or edit the placeholder)
// Example: PROJECT_ID=123 k6 run k6/k6_tests/heavy-get-cache-load.js
const PROJECT_ID = __ENV.PROJECT_ID || '1';

export const options = {
  stages: [
    { duration: '10s', target: Number(__ENV.VUS) || 100 },
    { duration: '10s', target: Number(__ENV.VUS) || 100 },
    { duration: '10s', target: Number(__ENV.VUS) || 150 },
    { duration: '10s', target: Number(__ENV.VUS) || 150 },
    { duration: '10s', target: Number(__ENV.VUS) || 200 },
    { duration: '10s', target: Number(__ENV.VUS) || 200 },
    { duration: '10s', target: Number(__ENV.VUS) || 250 },
    { duration: '10s', target: Number(__ENV.VUS) || 250 },
    { duration: '10s', target: Number(__ENV.VUS) || 500 },
    { duration: '10s', target: Number(__ENV.VUS) || 500 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

function buildHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (JWT_TOKEN) {
    headers['Authorization'] = `Bearer ${JWT_TOKEN}`;
  }

  return headers;
}

function hitListOrgs() {
  const res = http.get(`${BASE_URL}/v2/users/orgs`, {
    headers: buildHeaders(),
    tags: { endpoint: 'list_orgs' },
  });

  check(res, {
    'list_orgs status is 200': (r) => r.status === 200,
  });
}

function hitListUsersInOrg() {
  const res = http.get(`${BASE_URL}/v2/organizations/users?page=1&page_size=20`, {
    headers: buildHeaders(),
    tags: { endpoint: 'list_users_in_org' },
  });

  check(res, {
    'list_users_in_org status is 200 or 404': (r) => r.status === 200 || r.status === 404,
  });
}

function hitListProjects() {
  const res = http.get(`${BASE_URL}/v2/projects/?page=1&page_size=20`, {
    headers: buildHeaders(),
    tags: { endpoint: 'list_projects' },
  });

  check(res, {
    'list_projects status is 200 or 404': (r) => r.status === 200 || r.status === 404,
  });
}

function hitListProjectMembers() {
  const projectId = PROJECT_ID;

  const res = http.get(`${BASE_URL}/v2/projects/${projectId}/members`, {
    headers: buildHeaders(),
    tags: { endpoint: 'list_project_members' },
  });

  check(res, {
    'list_project_members status is 200 or 404': (r) => r.status === 200 || r.status === 404,
  });
}

export default function () {
  group('heavy_cached_get_endpoints', () => {
    group('list_orgs', () => {
      hitListOrgs();
    });

    group('list_users_in_org', () => {
      hitListUsersInOrg();
    });

    group('list_projects', () => {
      hitListProjects();
    });

    group('list_project_members', () => {
      hitListProjectMembers();
    });
  });

  sleep(1);
}

