-- Sources Table (for Web Verification)
CREATE TABLE public.sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.messages(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    relevance_score REAL,
    support_type TEXT NOT NULL CHECK (support_type IN ('supporting', 'contradicting', 'neutral')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX sources_message_id_idx ON public.sources(message_id);

-- Enable RLS
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view sources for their messages"
    ON public.sources FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.messages m 
            WHERE m.id = public.sources.message_id 
            AND m.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert sources for their messages"
    ON public.sources FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.messages m 
            WHERE m.id = public.sources.message_id 
            AND m.user_id = auth.uid()
        )
    );
