import test from 'node:test';
import assert from 'node:assert/strict';
import { getDeviceLocation } from '../src/lib/device-location.mjs';

test('device position records WGS84, accuracy and altitude without reusing cached positions', async () => {
  let options;
  const point = await getDeviceLocation({ secure: true, geolocation: { getCurrentPosition(success, _failure, value) { options = value; success({ coords: { latitude: 0, longitude: -73.64, accuracy: 8.25, altitude: 500 } }); } } });
  assert.deepEqual(point, { lat: '0.000000', lng: '-73.640000', source: 'device', uncertaintyM: '8.25', elevationM: '500.00' });
  assert.deepEqual(options, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
});
test('missing altitude stays unknown, and permission/timeout/unavailable cases are actionable', async () => {
  const point = await getDeviceLocation({ secure: true, geolocation: { getCurrentPosition(success) { success({ coords: { latitude: 4.15, longitude: -73.64, accuracy: 10, altitude: null } }); } } });
  assert.equal(point.elevationM, undefined);
  for (const [code, expected] of [[1, /permiso/], [2, /determinar/], [3, /tiempo/]]) await assert.rejects(getDeviceLocation({ secure: true, geolocation: { getCurrentPosition(_success, failure) { failure({ code }); } } }), expected);
  await assert.rejects(getDeviceLocation({ secure: false, geolocation: {} }), /HTTPS/);
  await assert.rejects(getDeviceLocation({ secure: true, geolocation: null }), /compatible/);
});
