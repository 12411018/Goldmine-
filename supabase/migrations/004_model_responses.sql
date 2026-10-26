-- Model Responses Table
CREATE TABLE public.model_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.messages(id) ON DELETE CASCADE NOT NULL,
    model_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    content TEXT NOT NULL,
    goldmine_score REAL,
    evaluation_signals JSONB,
    selected BOOLEAN DEFAULT false,
    latency_ms INTEGER,
    web_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX model_responses_message_id_idx ON public.model_responses(message_id);

-- Enable RLS
ALTER TABLE public.model_responses ENABLE ROW LEVEL SECURITY;

-- Policies (Viewable if user can view the message)
CREATE POLICY "Users can view model responses for their messages"
    ON public.model_responses FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.messages m 
            WHERE m.id = public.model_responses.message_id 
            AND m.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert model responses for their messages"
    ON public.model_responses FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.messages m 
            WHERE m.id = public.model_responses.message_id 
            AND m.user_id = auth.uid()
        )
    );
