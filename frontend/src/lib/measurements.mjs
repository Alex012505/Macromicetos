// Valores del enum public.measurement_type_enum de PostgreSQL y su unidad
// sugerida. La tabla no admite tipos libres ni medidas por hallazgo.
export const measurementTypes = [
  ['temperature', 'Temperatura', '°C'],
  ['relativeHumidity', 'Humedad relativa', '%'],
  ['atmosphericPressure', 'Presión atmosférica', 'hPa'],
  ['altitude', 'Altitud', 'm'],
  ['dewPoint', 'Punto de rocío', '°C'],
  ['heatIndex', 'Índice de calor', '°C'],
  ['windSpeed', 'Velocidad del viento', 'm/s'],
  ['windChill', 'Sensación térmica por viento', '°C'],
];
export const measurementLabel = type => measurementTypes.find(([key]) => key === type)?.[1] || type;
export const measurementUnit = type => measurementTypes.find(([key]) => key === type)?.[2] || '';
export function validateMeasurements(items = []) {
  const seen = new Set();
  for (const item of items) {
    if (!measurementTypes.some(([type]) => type === item.type)) throw new Error('Selecciona una variable ambiental válida.');
    if (seen.has(item.type)) throw new Error(`La variable «${measurementLabel(item.type)}» está repetida en la salida de campo.`);
    seen.add(item.type);
    const value = String(item.value ?? '').trim();
    if (!value) throw new Error(`Falta el valor de «${measurementLabel(item.type)}».`);
    if (!Number.isFinite(Number(value))) throw new Error(`El valor de «${measurementLabel(item.type)}» debe ser numérico.`);
    if (!String(item.unit ?? '').trim()) throw new Error(`Indica la unidad de «${measurementLabel(item.type)}».`);
  }
}
