import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import openapiTS, { astToString } from 'openapi-typescript';

const OPENAPI_URL = process.env.OPENAPI_URL || 'http://127.0.0.1:8000/openapi.json';
const OUTPUT_PATH = path.resolve('src/services/generated/schema.d.ts');

let schema;
try {
  const res = await fetch(OPENAPI_URL);
  if (res.ok) {
    schema = await res.json();
    console.log(`Fetched OpenAPI schema from ${OPENAPI_URL}`);
  }
} catch {
  // Not running, fallback to dumping directly from FastAPI app via python
}

if (!schema) {
  console.log('Backend server not running; generating OpenAPI schema directly from bck/app/main.py...');
  const pyCode = 'import json; from app.main import app; print(json.dumps(app.openapi()))';
  const raw = execSync(`uv run --project ../bck python -c "${pyCode}"`, {
    env: { ...process.env, JWT_SECRET: process.env.JWT_SECRET || '0123456789abcdef0123456789abcdef' },
    maxBuffer: 50 * 1024 * 1024,
  }).toString();
  schema = JSON.parse(raw);
}

const ast = await openapiTS(schema);
const output = astToString(ast);
fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
fs.writeFileSync(OUTPUT_PATH, output, 'utf-8');
console.log(`Successfully generated ${OUTPUT_PATH}`);
