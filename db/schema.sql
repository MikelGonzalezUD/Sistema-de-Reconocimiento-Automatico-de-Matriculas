CREATE TABLE IF NOT EXISTS vehiculos (
    vehiculo_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    matricula VARCHAR(20) UNIQUE NOT NULL CHECK (matricula = UPPER(matricula)),
    pais VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS camaras (
    camara_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ubicacion VARCHAR(100) NOT NULL,
    modelo VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS accesos (
    acceso_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehiculo_id INTEGER NOT NULL REFERENCES vehiculos(vehiculo_id) ON DELETE CASCADE,
    camara_id INTEGER NOT NULL REFERENCES camaras(camara_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confianza DECIMAL(5, 2) CHECK (confianza >= 0 AND confianza <= 100),
    matricula_img BYTEA
);

CREATE INDEX idx_accesos_timestamp ON accesos(timestamp);
CREATE INDEX idx_accesos_vehiculo ON accesos(vehiculo_id);
CREATE INDEX idx_accesos_camara ON accesos(camara_id);
CREATE INDEX idx_accesos_vehiculo_timestamp ON accesos(vehiculo_id, timestamp DESC);

-- Insertar una cámara de ejemplo (si no existe)
INSERT INTO camaras (ubicacion, modelo) 
VALUES ('Entrada Principal', 'Modelo A') 
ON CONFLICT DO NOTHING;