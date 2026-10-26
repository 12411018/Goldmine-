-- Additional provenance and safely stored extracted document text.
ALTER TABLE public.messages
    ADD COLUMN IF NOT EXISTS client_request_id UUID,
    ADD COLUMN IF NOT EXISTS provider_failures JSONB,
    ADD COLUMN IF NOT EXISTS web_research BOOLEAN NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS messages_client_request_id_key
    ON public.messages(client_request_id);

ALTER TABLE public.model_responses
    ADD COLUMN IF NOT EXISTS response_type TEXT NOT NULL DEFAULT 'model',
    ADD COLUMN IF NOT EXISTS selection_explanation TEXT;

ALTER TABLE public.attachments
    ADD COLUMN IF NOT EXISTS size_bytes INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS extracted_text TEXT;

-- Private bucket. Upload/download operations are performed by the backend only.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'chat-attachments',
    'chat-attachments',
    false,
    10485760,
    ARRAY['application/pdf', 'text/plain', 'text/markdown']
)
ON CONFLICT (id) DO UPDATE
SET public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;
