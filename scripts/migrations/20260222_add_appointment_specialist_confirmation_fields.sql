DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bookingstate')
       AND NOT EXISTS (
           SELECT 1
           FROM pg_enum e
           JOIN pg_type t ON t.oid = e.enumtypid
           WHERE t.typname = 'bookingstate'
             AND e.enumlabel = 'awaiting_specialist_confirmation'
       ) THEN
        ALTER TYPE bookingstate ADD VALUE 'awaiting_specialist_confirmation';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bookingstate')
       AND NOT EXISTS (
           SELECT 1
           FROM pg_enum e
           JOIN pg_type t ON t.oid = e.enumtypid
           WHERE t.typname = 'bookingstate'
             AND e.enumlabel = 'rejected_by_specialist'
       ) THEN
        ALTER TYPE bookingstate ADD VALUE 'rejected_by_specialist';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_state')
       AND NOT EXISTS (
           SELECT 1
           FROM pg_enum e
           JOIN pg_type t ON t.oid = e.enumtypid
           WHERE t.typname = 'booking_state'
             AND e.enumlabel = 'awaiting_specialist_confirmation'
       ) THEN
        ALTER TYPE booking_state ADD VALUE 'awaiting_specialist_confirmation';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_state')
       AND NOT EXISTS (
           SELECT 1
           FROM pg_enum e
           JOIN pg_type t ON t.oid = e.enumtypid
           WHERE t.typname = 'booking_state'
             AND e.enumlabel = 'rejected_by_specialist'
       ) THEN
        ALTER TYPE booking_state ADD VALUE 'rejected_by_specialist';
    END IF;
END
$$;

ALTER TABLE appointment
ADD COLUMN IF NOT EXISTS rejection_reason TEXT NULL,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ NULL;
