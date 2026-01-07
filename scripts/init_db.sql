

-- ==========================================================
-- SCRIPT COMPLET : VEHICLE DOMAIN MODEL (POSTGRESQL)
-- Basé sur le diagramme UML fourni
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Nettoyage complet
DROP TABLE IF EXISTS vehicle_review CASCADE;
DROP TABLE IF EXISTS vehicle_illustration_image CASCADE;
DROP TABLE IF EXISTS vehicle_can_transport CASCADE;
DROP TABLE IF EXISTS vehicle_keyword CASCADE;
DROP TABLE IF EXISTS vehicle_amenity CASCADE;
DROP TABLE IF EXISTS vehicle_ownership CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS party CASCADE;
DROP TABLE IF EXISTS vehicle_make CASCADE;
DROP TABLE IF EXISTS vehicle_model CASCADE;
DROP TABLE IF EXISTS transmission_type CASCADE;
DROP TABLE IF EXISTS fuel_type CASCADE;
DROP TABLE IF EXISTS vehicle_type CASCADE;
DROP TABLE IF EXISTS vehicle_size CASCADE;
DROP TABLE IF EXISTS manufacturer CASCADE;

DROP TABLE IF EXISTS livreurs CASCADE;
DROP TABLE IF EXISTS personnes CASCADE;
DROP TABLE IF EXISTS comments CASCADE;

-- 1. TABLES DE RÉFÉRENCE (LOOKUP TABLES)
-- ==========================================================

CREATE TABLE vehicle_make (
    vehicle_make_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    make_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicle_model (
    vehicle_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transmission_type (
    transmission_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_name TEXT NOT NULL UNIQUE, -- ex: 'Manual 2WD', 'Automatic 4WD'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fuel_type (
    fuel_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fuel_type_name TEXT NOT NULL UNIQUE, -- ex: 'Petrol', 'Diesel', 'Electric'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicle_type (
    vehicle_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_name TEXT NOT NULL UNIQUE, -- ex: 'Commercial', 'Sport', 'Personal'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicle_size (
    vehicle_size_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    size_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE manufacturer (
    manufacturer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manufacturer_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ENTITÉ PARTY (Le socle pour Freelance, Agences, etc.)
-- ==========================================================

CREATE TABLE party (
    party_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    display_name TEXT NOT NULL,
    phone TEXT,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. ENTITÉ CENTRALE : VEHICLE
-- ==========================================================

CREATE TABLE vehicles (
    vehicle_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Clés étrangères de référence
    vehicle_make_id UUID REFERENCES vehicle_make(vehicle_make_id),
    vehicle_model_id UUID REFERENCES vehicle_model(vehicle_model_id),
    transmission_type_id UUID REFERENCES transmission_type(transmission_type_id),
    manufacturer_id UUID REFERENCES manufacturer(manufacturer_id),
    vehicle_size_id UUID REFERENCES vehicle_size(vehicle_size_id),
    vehicle_type_id UUID REFERENCES vehicle_type(vehicle_type_id),
    fuel_type_id UUID REFERENCES fuel_type(fuel_type_id),

    -- Identification et Photos (Support TEXT pour URLs ou BYTEA pour données binaires)
    vehicle_serial_number TEXT UNIQUE,
    vehicle_serial_photo TEXT,
    registration_number TEXT UNIQUE,
    registration_photo TEXT,
    registration_expiry_date TIMESTAMP,

    -- Spécifications techniques
    tank_capacity NUMERIC(10,2),
    luggage_max_capacity NUMERIC(10,2),
    total_seat_number INTEGER,

    -- Métriques de performance
    average_fuel_consumption_per_km NUMERIC(10,2),
    mileage_at_start NUMERIC(15,2),
    mileage_since_commissioning NUMERIC(15,2),
    vehicle_age_at_start NUMERIC(5,2),

    -- Champs additionnels
    brand TEXT, -- Dénormalisation optionnelle pour la recherche rapide

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLES DE LIAISON ET DÉTAILS (RELATIONS 0..*)
-- ==========================================================

-- Relation Ownership (Propriété et Usage)
CREATE TABLE vehicle_ownership (
    vehicle_ownership_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    party_id UUID NOT NULL REFERENCES party(party_id) ON DELETE CASCADE,
    usage_role TEXT NOT NULL, -- ex: 'DRIVER', 'LOGISTICS', 'FLEET', 'OWNER'
    is_primary BOOLEAN DEFAULT FALSE,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aménagements (A/C, GPS, etc.)
CREATE TABLE vehicle_amenity (
    amenity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    amenity_name TEXT NOT NULL, -- ex: 'Confort/Commodities'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mots-clés (Delivery, 4WD, etc.)
CREATE TABLE vehicle_keyword (
    keyword_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Capacité de transport (Animaux, Marchandises, Humains)
CREATE TABLE vehicle_can_transport (
    transport_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    item TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Images d'illustration
CREATE TABLE vehicle_illustration_image (
    image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    image_path TEXT,
    image_data BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Avis et Reviews
CREATE TABLE vehicle_review (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    review_text TEXT,
    rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. AUTOMATISATION DES TIMESTAMPS
-- ==========================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER tr_update_vehicles BEFORE UPDATE ON vehicles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER tr_update_party BEFORE UPDATE ON party FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();






-- 1. Marques et Modèles
INSERT INTO vehicle_make (make_name) VALUES
('Toyota'), ('Mercedes-Benz'), ('Suzuki'), ('Mitsubishi'), ('Hyundai');

INSERT INTO vehicle_model (model_name) VALUES
('Hilux'), ('V-Class'), ('S-Presso'), ('L200'), ('Santa Fe');

-- 2. Transmissions et Carburants
INSERT INTO transmission_type (type_name) VALUES
('Manual 6-Speed'), ('Automatic'), ('4WD Manual'), ('CVT'), ('Dual-Clutch');

INSERT INTO fuel_type (fuel_type_name) VALUES
('Diesel'), ('Petrol'), ('Electric'), ('Hybrid'), ('LPG');

-- 3. Types et Tailles
INSERT INTO vehicle_type (type_name) VALUES
('Commercial'), ('Luxury'), ('Personal'), ('SUV'), ('Pickup');

INSERT INTO vehicle_size (size_name) VALUES
('Compact'), ('Intermediate'), ('Full-Size'), ('Large'), ('Extra-Large');

-- 4. Constructeurs
INSERT INTO manufacturer (manufacturer_name) VALUES
('Toyota Motor Corp'), ('Daimler AG'), ('Suzuki Motor'), ('Mitsubishi Motors'), ('Hyundai Motor Group');

-- 5. Propriétaires / Tiers (Party)
INSERT INTO party (display_name, phone, email) VALUES
('Logistique Express', '+237 600112233', 'contact@log-express.cm'),
('VIP Services Douala', '+237 600445566', 'info@vip-douala.cm'),
('Freelance Driver Alpha', '+237 600778899', 'alpha.driver@gmail.com');



DO $$
DECLARE
    make_id UUID; model_id UUID; trans_id UUID; fuel_id UUID;
    type_id UUID; size_id UUID; manuf_id UUID;
BEGIN
    -- Boucle pour générer 15 véhicules avec des variations
    FOR i IN 1..15 LOOP
        -- Sélection aléatoire des IDs pour la cohérence
        SELECT vehicle_make_id INTO make_id FROM vehicle_make ORDER BY random() LIMIT 1;
        SELECT vehicle_model_id INTO model_id FROM vehicle_model ORDER BY random() LIMIT 1;
        SELECT transmission_type_id INTO trans_id FROM transmission_type ORDER BY random() LIMIT 1;
        SELECT fuel_type_id INTO fuel_id FROM fuel_type ORDER BY random() LIMIT 1;
        SELECT vehicle_type_id INTO type_id FROM vehicle_type ORDER BY random() LIMIT 1;
        SELECT vehicle_size_id INTO size_id FROM vehicle_size ORDER BY random() LIMIT 1;
        SELECT manufacturer_id INTO manuf_id FROM manufacturer ORDER BY random() LIMIT 1;

        INSERT INTO vehicles (
            vehicle_make_id, vehicle_model_id, transmission_type_id,
            manufacturer_id, vehicle_size_id, vehicle_type_id, fuel_type_id,
            vehicle_serial_number, registration_number, registration_expiry_date,
            tank_capacity, luggage_max_capacity, total_seat_number,
            average_fuel_consumption_per_km, mileage_at_start, mileage_since_commissioning,
            vehicle_age_at_start, brand
        ) VALUES (
            make_id, model_id, trans_id,
            manuf_id, size_id, type_id, fuel_id,
            'VIN-' || i || '-' || floor(random()*1000000)::text, -- Numéro de série unique
            'REG-' || (100 + i) || '-LT', -- Plaque d'immatriculation
            NOW() + (random() * (interval '730 days')), -- Expiration future
            (CASE WHEN i % 2 = 0 THEN 80.0 ELSE 55.0 END), -- Capacité réservoir cohérente
            (CASE WHEN i % 3 = 0 THEN 1000.0 ELSE 450.0 END), -- Bagages
            (CASE WHEN i % 5 = 0 THEN 7 ELSE 5 END), -- Nombre de places
            (CASE WHEN fuel_id = (SELECT fuel_type_id FROM fuel_type WHERE fuel_type_name = 'Diesel') THEN 0.08 ELSE 0.12 END),
            random() * 50000, -- Kilométrage au départ
            random() * 100000, -- Kilométrage total
            random() * 10, -- Âge du véhicule
            (SELECT make_name FROM vehicle_make WHERE vehicle_make_id = make_id)
        );
    END LOOP;
END $$;


-- Assigner chaque véhicule à un propriétaire avec un rôle spécifique
INSERT INTO vehicle_ownership (vehicle_id, party_id, usage_role, is_primary)
SELECT
    v.vehicle_id,
    (SELECT party_id FROM party ORDER BY random() LIMIT 1),
    (CASE WHEN v.total_seat_number > 5 THEN 'LOGISTICS' ELSE 'OWNER' END),
    TRUE
FROM vehicles v;

-- Ajouter des équipements (Amenities) pour les 15 véhicules
INSERT INTO vehicle_amenity (vehicle_id, amenity_name)
SELECT vehicle_id, unnest(ARRAY['Air Conditioning', 'GPS Tracking', 'Spare Tire'])
FROM vehicles;

-- Ajouter des mots-clés (Keywords)
INSERT INTO vehicle_keyword (vehicle_id, keyword)
SELECT vehicle_id, unnest(ARRAY['Delivery', '4WD', 'City-Friendly'])
FROM vehicles;








-- Database Initialization Script
-- Creates tables for the Sentiment Recommendation System
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS personnes CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Personnes (Clients) table
CREATE TABLE IF NOT EXISTS personnes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_client VARCHAR(100) UNIQUE NOT NULL,
    nom VARCHAR(255) NOT NULL,
    telephone VARCHAR(50),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    cni VARCHAR(100),
    carte_photo TEXT,
    extrait_du_cassier TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Livreurs table
CREATE TABLE IF NOT EXISTS livreurs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statut VARCHAR(50) DEFAULT 'disponible',
    reputation FLOAT DEFAULT 0.0,
    localisation VARCHAR(255),
    registre_commerce VARCHAR(255),
    nom_commerciale VARCHAR(255),
    nui VARCHAR(100) UNIQUE,
    disponible BOOLEAN DEFAULT TRUE,
    nombre_livraisons INTEGER DEFAULT 0,
    note_moyenne FLOAT DEFAULT 0.0,
    zone_couverture TEXT,
    personne_id UUID REFERENCES personnes(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_livreurs_statut ON livreurs(statut);
CREATE INDEX IF NOT EXISTS idx_livreurs_disponible ON livreurs(disponible);
CREATE INDEX IF NOT EXISTS idx_vehicles_disponible ON vehicles(disponible);
CREATE INDEX IF NOT EXISTS idx_vehicles_brand ON vehicles(brand);
CREATE INDEX IF NOT EXISTS idx_vehicles_registration ON vehicles(registration_number);
CREATE INDEX IF NOT EXISTS idx_comments_product ON comments(product_id, product_type);
CREATE INDEX IF NOT EXISTS idx_comments_client ON comments(client_id);
CREATE INDEX IF NOT EXISTS idx_personnes_email ON personnes(email);
CREATE INDEX IF NOT EXISTS idx_personnes_id_client ON personnes(id_client);

-- Insert sample data for testing
INSERT INTO personnes (id_client, nom, telephone, email, password) VALUES
    ('client_001', 'Jean Dupont', '+237 699 123 456', 'jean.dupont@example.com', '$2b$12$hash'),
    ('client_002', 'Marie Martin', '+237 677 234 567', 'marie.martin@example.com', '$2b$12$hash'),
    ('client_003', 'Paul Bernard', '+237 655 345 678', 'paul.bernard@example.com', '$2b$12$hash')
ON CONFLICT DO NOTHING;

INSERT INTO livreurs (statut, reputation, localisation, nom_commerciale, nui, disponible, nombre_livraisons, note_moyenne, zone_couverture) VALUES
    ('disponible', 4.5, 'Douala, Cameroun', 'Express Livraison', 'NUI001', TRUE, 150, 4.5, 'Douala Centre, Akwa, Bonapriso'),
    ('disponible', 4.2, 'Yaoundé, Cameroun', 'Rapide Service', 'NUI002', TRUE, 89, 4.2, 'Yaoundé Centre, Bastos, Mvan'),
    ('occupe', 4.8, 'Douala, Cameroun', 'Flash Delivery', 'NUI003', FALSE, 230, 4.8, 'Douala, Bonaberi, Deido'),
    ('disponible', 3.9, 'Bafoussam, Cameroun', 'West Express', 'NUI004', TRUE, 45, 3.9, 'Bafoussam Centre')
ON CONFLICT DO NOTHING;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_personnes_updated_at ON personnes;
CREATE TRIGGER update_personnes_updated_at
    BEFORE UPDATE ON personnes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_livreurs_updated_at ON livreurs;
CREATE TRIGGER update_livreurs_updated_at
    BEFORE UPDATE ON livreurs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_vehicles_updated_at ON vehicles;
CREATE TRIGGER update_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
