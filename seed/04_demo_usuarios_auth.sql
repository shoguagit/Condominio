-- Seed: Crear usuarios demo en Supabase Auth
-- Contraseña: Condominio123

BEGIN;

DO $$
DECLARE
    v_admin_email TEXT := 'admin.demo@condominio.local';
    v_operador_email TEXT := 'operador.demo@condominio.local';
    v_password TEXT := 'Condominio123';
    
    v_admin_id UUID;
    v_operador_id UUID;
BEGIN
    -- Buscar si ya existen
    SELECT id INTO v_admin_id FROM auth.users WHERE email = v_admin_email LIMIT 1;
    SELECT id INTO v_operador_id FROM auth.users WHERE email = v_operador_email LIMIT 1;
    
    -- Admin Demo
    IF v_admin_id IS NULL THEN
        INSERT INTO auth.users (
            id, instance_id, aud, role, email, encrypted_password,
            email_confirmed_at, created_at, updated_at,
            is_super_admin, is_anonymous,
            confirmation_token, confirmation_sent_at,
            recovery_token, recovery_sent_at,
            email_change_token_new, email_change, email_change_sent_at,
            email_change_token_current,
            reauthentication_token, reauthentication_sent_at
        )
        VALUES (
            gen_random_uuid(),
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            v_admin_email,
            crypt(v_password, gen_salt('bf')),
            now(),
            now(),
            now(),
            FALSE,
            FALSE,
            '',
            now(),
            '',
            now(),
            '', '',
            now(),
            '',
            '',
            now()
        )
        RETURNING id INTO v_admin_id;
    END IF;

    -- Operador Demo
    IF v_operador_id IS NULL THEN
        INSERT INTO auth.users (
            id, instance_id, aud, role, email, encrypted_password,
            email_confirmed_at, created_at, updated_at,
            is_super_admin, is_anonymous,
            confirmation_token, confirmation_sent_at,
            recovery_token, recovery_sent_at,
            email_change_token_new, email_change, email_change_sent_at,
            email_change_token_current,
            reauthentication_token, reauthentication_sent_at
        )
        VALUES (
            gen_random_uuid(),
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            v_operador_email,
            crypt(v_password, gen_salt('bf')),
            now(),
            now(),
            now(),
            FALSE,
            FALSE,
            '',
            now(),
            '',
            now(),
            '', '',
            now(),
            '',
            '',
            now()
        )
        RETURNING id INTO v_operador_id;
    END IF;

    RAISE NOTICE 'Usuarios demo creados: admin_id=%, operador_id=%', v_admin_id, v_operador_id;
END $$;

COMMIT;