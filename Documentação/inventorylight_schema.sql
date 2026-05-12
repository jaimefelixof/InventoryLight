-- ============================================================
-- InventoryLight — Schema SQL v1.0
-- Banco: Supabase (PostgreSQL)
-- Modelo: Admin vê tudo | Usuário vê apenas seu setor
-- ============================================================

-- ── 1. SETORES ───────────────────────────────────────────────
CREATE TABLE public.setores (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome      TEXT NOT NULL UNIQUE,
    ativo     BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 2. PERFIS DE USUÁRIO ─────────────────────────────────────
-- Estende auth.users do Supabase Auth
CREATE TABLE public.perfis (
    id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nome       TEXT NOT NULL,
    papel      TEXT NOT NULL CHECK (papel IN ('admin', 'usuario')),
    setor_id   UUID REFERENCES public.setores(id),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- setor_id pode ser NULL para admin (acessa tudo)

-- ── 3. ATIVOS ────────────────────────────────────────────────
CREATE TABLE public.ativos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome              TEXT NOT NULL,
    tipo              TEXT NOT NULL CHECK (tipo IN ('hardware', 'software', 'outro')),
    numero_serie      TEXT,
    setor_id          UUID NOT NULL REFERENCES public.setores(id),
    status            TEXT NOT NULL DEFAULT 'ativo'
                          CHECK (status IN ('ativo', 'em_manutencao', 'desativado')),
    data_aquisicao    DATE,
    data_garantia     DATE,
    observacoes       TEXT,
    deletado          BOOLEAN NOT NULL DEFAULT FALSE,  -- soft delete
    criado_por        UUID REFERENCES auth.users(id),
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 4. LICENÇAS ──────────────────────────────────────────────
CREATE TABLE public.licencas (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ativo_id       UUID NOT NULL REFERENCES public.ativos(id) ON DELETE CASCADE,
    software       TEXT NOT NULL,
    chave          TEXT,
    validade        DATE,
    deletado       BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 5. HISTÓRICO DE ALTERAÇÕES ───────────────────────────────
CREATE TABLE public.historico (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ativo_id     UUID NOT NULL REFERENCES public.ativos(id) ON DELETE CASCADE,
    usuario_id   UUID REFERENCES auth.users(id),
    campo        TEXT NOT NULL,
    valor_antes  TEXT,
    valor_depois TEXT,
    alterado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 6. ÍNDICES ───────────────────────────────────────────────
CREATE INDEX idx_ativos_setor    ON public.ativos(setor_id);
CREATE INDEX idx_ativos_status   ON public.ativos(status);
CREATE INDEX idx_ativos_garantia ON public.ativos(data_garantia);
CREATE INDEX idx_ativos_deletado ON public.ativos(deletado);
CREATE INDEX idx_historico_ativo ON public.historico(ativo_id);

-- ── 7. TRIGGER: atualizado_em automático ─────────────────────
CREATE OR REPLACE FUNCTION public.set_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ativos_atualizado_em
    BEFORE UPDATE ON public.ativos
    FOR EACH ROW EXECUTE FUNCTION public.set_atualizado_em();

-- ── 8. ROW LEVEL SECURITY ────────────────────────────────────
ALTER TABLE public.ativos    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.licencas  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.historico ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfis    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.setores   ENABLE ROW LEVEL SECURITY;

-- Função auxiliar: retorna papel do usuário logado
CREATE OR REPLACE FUNCTION public.meu_papel()
RETURNS TEXT AS $$
    SELECT papel FROM public.perfis WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- Função auxiliar: retorna setor_id do usuário logado
CREATE OR REPLACE FUNCTION public.meu_setor()
RETURNS UUID AS $$
    SELECT setor_id FROM public.perfis WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- SETORES: todos leem, só admin escreve
CREATE POLICY "setores_leitura" ON public.setores
    FOR SELECT USING (TRUE);

CREATE POLICY "setores_escrita_admin" ON public.setores
    FOR ALL USING (public.meu_papel() = 'admin');

-- PERFIS: cada um vê o próprio, admin vê todos
CREATE POLICY "perfis_proprio" ON public.perfis
    FOR SELECT USING (id = auth.uid() OR public.meu_papel() = 'admin');

CREATE POLICY "perfis_escrita_admin" ON public.perfis
    FOR ALL USING (public.meu_papel() = 'admin');

-- ATIVOS: admin vê tudo; usuário vê só seu setor
CREATE POLICY "ativos_admin" ON public.ativos
    FOR ALL USING (public.meu_papel() = 'admin');

CREATE POLICY "ativos_usuario_setor" ON public.ativos
    FOR SELECT USING (
        public.meu_papel() = 'usuario'
        AND setor_id = public.meu_setor()
        AND deletado = FALSE
    );

-- LICENÇAS: herda acesso via ativo
CREATE POLICY "licencas_admin" ON public.licencas
    FOR ALL USING (public.meu_papel() = 'admin');

CREATE POLICY "licencas_usuario_setor" ON public.licencas
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.ativos a
            WHERE a.id = ativo_id
              AND a.setor_id = public.meu_setor()
              AND a.deletado = FALSE
        )
        AND public.meu_papel() = 'usuario'
    );

-- HISTÓRICO: admin vê tudo; usuário vê só seu setor
CREATE POLICY "historico_admin" ON public.historico
    FOR ALL USING (public.meu_papel() = 'admin');

CREATE POLICY "historico_usuario_setor" ON public.historico
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.ativos a
            WHERE a.id = ativo_id
              AND a.setor_id = public.meu_setor()
        )
        AND public.meu_papel() = 'usuario'
    );

-- ── 9. DADOS INICIAIS ────────────────────────────────────────
INSERT INTO public.setores (nome) VALUES
    ('TI'),
    ('Administrativo'),
    ('Financeiro'),
    ('Operacional'),
    ('RH');
