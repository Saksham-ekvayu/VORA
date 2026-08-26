--
-- PostgreSQL database dump
--

\restrict UU7oOx8q7XC9yeJDj3797kAh5UWVcYCZf4uQPd9IUjGeDVRdpb0Ml2oZpKdQN5V

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_prompts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_prompts (
    id character varying(24) NOT NULL,
    name character varying NOT NULL,
    prompt text NOT NULL,
    meta jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    id character varying(24) NOT NULL,
    "tenantId" character varying NOT NULL,
    name character varying NOT NULL,
    email character varying NOT NULL,
    phone character varying,
    "secondaryPhone" character varying,
    "isActive" boolean DEFAULT true NOT NULL,
    avatar character varying,
    address jsonb NOT NULL,
    "createdBy" jsonb NOT NULL,
    "createdAt" timestamp with time zone,
    "updatedAt" timestamp with time zone
);


--
-- Name: deployment_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployment_documents (
    id character varying(24) NOT NULL,
    "tenantId" character varying NOT NULL,
    "deploymentFrameworkId" character varying(24) NOT NULL,
    "frameworkName" character varying NOT NULL,
    "frameworkCode" character varying,
    "frameworkVersion" character varying,
    "uploadedBy" character varying(24) NOT NULL,
    document jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: deployment_frameworks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployment_frameworks (
    id character varying(24) NOT NULL,
    "tenantId" character varying NOT NULL,
    "assignedFrameworkId" character varying(24) NOT NULL,
    "frameworkId" character varying,
    "frameworkName" character varying NOT NULL,
    "frameworkCategoryId" character varying,
    "frameworkCode" character varying,
    "frameworkVersion" character varying,
    "uploadedBy" character varying(24) NOT NULL,
    "currentPackageVersion" character varying NOT NULL,
    packages jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: deployment_package_merges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployment_package_merges (
    id character varying(24) NOT NULL,
    status character varying(20) NOT NULL,
    "fileHashes" jsonb NOT NULL,
    controls jsonb NOT NULL,
    summary jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: document_extractions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_extractions (
    id character varying(24) NOT NULL,
    "fileHash" character varying NOT NULL,
    "aiExtraction" jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: evidence_output; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evidence_output (
    id character varying(24) NOT NULL,
    control_id character varying,
    output jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: framework_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.framework_assignments (
    id character varying(24) NOT NULL,
    "tenantId" character varying NOT NULL,
    "customerId" character varying(24) NOT NULL,
    "frameworkId" character varying(24) NOT NULL,
    "frameworkCode" character varying NOT NULL,
    "frameworkName" character varying,
    "frameworkVersion" character varying,
    "frameworkCategoryId" character varying,
    "uploadedBy" character varying(24),
    "currentFileVersion" character varying NOT NULL,
    "fileVersions" jsonb NOT NULL,
    status character varying NOT NULL,
    assignment jsonb NOT NULL,
    revocation jsonb NOT NULL,
    finalization jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: framework_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.framework_categories (
    id character varying(24) NOT NULL,
    code character varying NOT NULL,
    "frameworkCategoryName" character varying NOT NULL,
    description text NOT NULL,
    "isActive" boolean DEFAULT true NOT NULL,
    "createdBy" character varying(24) NOT NULL,
    "updatedBy" character varying(24),
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: framework_category_access; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.framework_category_access (
    id character varying(24) NOT NULL,
    "expertId" character varying(24) NOT NULL,
    "frameworkCategoryId" character varying(24) NOT NULL,
    "frameworkCode" character varying NOT NULL,
    status character varying NOT NULL,
    "requestedBy" character varying NOT NULL,
    approval jsonb NOT NULL,
    rejection jsonb NOT NULL,
    revocation jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: framework_merges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.framework_merges (
    id character varying(24) NOT NULL,
    "mergeHashes" jsonb NOT NULL,
    controls jsonb NOT NULL,
    summary jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: frameworks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.frameworks (
    id character varying(24) NOT NULL,
    "frameworkName" character varying NOT NULL,
    "frameworkVersion" character varying NOT NULL,
    "frameworkCategoryId" character varying(24) NOT NULL,
    "frameworkCode" character varying NOT NULL,
    "uploadedBy" character varying(24) NOT NULL,
    "currentFileVersion" character varying NOT NULL,
    "fileVersions" jsonb NOT NULL,
    approval jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: gap_threshold_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gap_threshold_config (
    id character varying(24) NOT NULL,
    is_active boolean NOT NULL,
    implemented_threshold double precision NOT NULL,
    partially_implemented_threshold double precision NOT NULL,
    not_implemented_threshold double precision NOT NULL,
    implemented_label character varying NOT NULL,
    partially_implemented_label character varying NOT NULL,
    not_implemented_label character varying NOT NULL,
    description character varying,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: package_comparisons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.package_comparisons (
    id character varying(24) NOT NULL,
    "deploymentFrameworkId" character varying(24),
    "fileHashes" jsonb NOT NULL,
    comparison jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: package_gap_analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.package_gap_analyses (
    id character varying(24) NOT NULL,
    "deploymentFrameworkId" character varying(24),
    "fileHashes" jsonb NOT NULL,
    "gapAnalysis" jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: processed_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processed_files (
    id integer NOT NULL,
    file_path character varying NOT NULL,
    status character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: processed_files_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.processed_files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: processed_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.processed_files_id_seq OWNED BY public.processed_files.id;


--
-- Name: source_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_configs (
    id integer NOT NULL,
    control_name character varying NOT NULL,
    dp_name character varying NOT NULL,
    organization_name character varying NOT NULL,
    source_type character varying NOT NULL,
    source_name character varying,
    is_active integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.source_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: source_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.source_configs_id_seq OWNED BY public.source_configs.id;


--
-- Name: source_credentials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_credentials (
    id integer NOT NULL,
    source_config_id integer NOT NULL,
    config_json text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_credentials_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.source_credentials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: source_credentials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.source_credentials_id_seq OWNED BY public.source_credentials.id;


--
-- Name: uploaded_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uploaded_files (
    id character varying(24) NOT NULL,
    ref_id character varying(24),
    filename character varying NOT NULL,
    file_path character varying,
    s3_url character varying,
    meta jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying(24) NOT NULL,
    "tenantId" character varying,
    avatar character varying,
    name character varying NOT NULL,
    email character varying NOT NULL,
    phone character varying,
    "secondaryPhone" character varying,
    role character varying NOT NULL,
    designation character varying,
    password character varying NOT NULL,
    "isEmailVerified" boolean DEFAULT false NOT NULL,
    "isActive" boolean DEFAULT true NOT NULL,
    otp jsonb,
    "tokenVersion" integer DEFAULT 0 NOT NULL,
    address jsonb NOT NULL,
    "createdBy" jsonb NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


--
-- Name: processed_files id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_files ALTER COLUMN id SET DEFAULT nextval('public.processed_files_id_seq'::regclass);


--
-- Name: source_configs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_configs ALTER COLUMN id SET DEFAULT nextval('public.source_configs_id_seq'::regclass);


--
-- Name: source_credentials id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_credentials ALTER COLUMN id SET DEFAULT nextval('public.source_credentials_id_seq'::regclass);


--
-- Name: agent_prompts agent_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_prompts
    ADD CONSTRAINT agent_prompts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: deployment_documents deployment_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployment_documents
    ADD CONSTRAINT deployment_documents_pkey PRIMARY KEY (id);


--
-- Name: deployment_frameworks deployment_frameworks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployment_frameworks
    ADD CONSTRAINT deployment_frameworks_pkey PRIMARY KEY (id);


--
-- Name: deployment_package_merges deployment_package_merges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployment_package_merges
    ADD CONSTRAINT deployment_package_merges_pkey PRIMARY KEY (id);


--
-- Name: document_extractions document_extractions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_extractions
    ADD CONSTRAINT document_extractions_pkey PRIMARY KEY (id);


--
-- Name: evidence_output evidence_output_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence_output
    ADD CONSTRAINT evidence_output_pkey PRIMARY KEY (id);


--
-- Name: framework_assignments framework_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework_assignments
    ADD CONSTRAINT framework_assignments_pkey PRIMARY KEY (id);


--
-- Name: framework_categories framework_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework_categories
    ADD CONSTRAINT framework_categories_pkey PRIMARY KEY (id);


--
-- Name: framework_category_access framework_category_access_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework_category_access
    ADD CONSTRAINT framework_category_access_pkey PRIMARY KEY (id);


--
-- Name: framework_merges framework_merges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework_merges
    ADD CONSTRAINT framework_merges_pkey PRIMARY KEY (id);


--
-- Name: frameworks frameworks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frameworks
    ADD CONSTRAINT frameworks_pkey PRIMARY KEY (id);


--
-- Name: gap_threshold_config gap_threshold_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gap_threshold_config
    ADD CONSTRAINT gap_threshold_config_pkey PRIMARY KEY (id);


--
-- Name: package_comparisons package_comparisons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.package_comparisons
    ADD CONSTRAINT package_comparisons_pkey PRIMARY KEY (id);


--
-- Name: package_gap_analyses package_gap_analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.package_gap_analyses
    ADD CONSTRAINT package_gap_analyses_pkey PRIMARY KEY (id);


--
-- Name: processed_files processed_files_file_path_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_files
    ADD CONSTRAINT processed_files_file_path_key UNIQUE (file_path);


--
-- Name: processed_files processed_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_files
    ADD CONSTRAINT processed_files_pkey PRIMARY KEY (id);


--
-- Name: source_configs source_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_configs
    ADD CONSTRAINT source_configs_pkey PRIMARY KEY (id);


--
-- Name: source_credentials source_credentials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_credentials
    ADD CONSTRAINT source_credentials_pkey PRIMARY KEY (id);


--
-- Name: uploaded_files uploaded_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uploaded_files
    ADD CONSTRAINT uploaded_files_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_customers_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customers_active ON public.customers USING btree ("isActive");


--
-- Name: ix_customers_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customers_created ON public.customers USING btree ("createdAt");


--
-- Name: ix_customers_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_customers_email ON public.customers USING btree (email);


--
-- Name: ix_customers_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_customers_tenant ON public.customers USING btree ("tenantId");


--
-- Name: ix_dd_df_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dd_df_id ON public.deployment_documents USING btree ("deploymentFrameworkId");


--
-- Name: ix_dd_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dd_tenant_created ON public.deployment_documents USING btree ("tenantId", "createdAt");


--
-- Name: ix_dd_tenant_uploader; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dd_tenant_uploader ON public.deployment_documents USING btree ("tenantId", "uploadedBy");


--
-- Name: ix_deployment_package_merge_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_deployment_package_merge_created ON public.deployment_package_merges USING btree ("createdAt");


--
-- Name: ix_df_tenant_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_df_tenant_category ON public.deployment_frameworks USING btree ("tenantId", "frameworkCategoryId");


--
-- Name: ix_df_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_df_tenant_created ON public.deployment_frameworks USING btree ("tenantId", "createdAt");


--
-- Name: ix_df_tenant_uploader; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_df_tenant_uploader ON public.deployment_frameworks USING btree ("tenantId", "uploadedBy");


--
-- Name: ix_doc_extractions_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_doc_extractions_hash ON public.document_extractions USING btree ("fileHash");


--
-- Name: ix_evidence_control; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evidence_control ON public.evidence_output USING btree (control_id);


--
-- Name: ix_fa_tenant_customer_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fa_tenant_customer_status ON public.framework_assignments USING btree ("tenantId", "customerId", status);


--
-- Name: ix_fa_tenant_customer_ver; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_fa_tenant_customer_ver ON public.framework_assignments USING btree ("tenantId", "customerId", "frameworkVersion");


--
-- Name: ix_fca_code_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fca_code_status ON public.framework_category_access USING btree ("frameworkCode", status);


--
-- Name: ix_fca_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fca_created ON public.framework_category_access USING btree ("createdAt");


--
-- Name: ix_fca_expert_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_fca_expert_code ON public.framework_category_access USING btree ("expertId", "frameworkCode");


--
-- Name: ix_fca_expert_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fca_expert_status ON public.framework_category_access USING btree ("expertId", status);


--
-- Name: ix_framework_categories_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_framework_categories_active ON public.framework_categories USING btree ("isActive");


--
-- Name: ix_framework_categories_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_framework_categories_code ON public.framework_categories USING btree (code);


--
-- Name: ix_framework_categories_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_framework_categories_created ON public.framework_categories USING btree ("createdAt");


--
-- Name: ix_framework_categories_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_framework_categories_created_by ON public.framework_categories USING btree ("createdBy");


--
-- Name: ix_framework_categories_updated_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_framework_categories_updated_by ON public.framework_categories USING btree ("updatedBy");


--
-- Name: ix_framework_merges_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_framework_merges_created ON public.framework_merges USING btree ("createdAt");


--
-- Name: ix_frameworks_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_frameworks_created ON public.frameworks USING btree ("createdAt");


--
-- Name: ix_frameworks_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_frameworks_uploaded_by ON public.frameworks USING btree ("uploadedBy");


--
-- Name: ix_frameworks_uploader_cat_ver; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_frameworks_uploader_cat_ver ON public.frameworks USING btree ("uploadedBy", "frameworkCategoryId", "frameworkVersion");


--
-- Name: ix_gap_threshold_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_gap_threshold_unique ON public.gap_threshold_config USING btree (is_active);


--
-- Name: ix_processed_files_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_processed_files_id ON public.processed_files USING btree (id);


--
-- Name: ix_source_configs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_configs_id ON public.source_configs USING btree (id);


--
-- Name: ix_source_credentials_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_credentials_id ON public.source_credentials USING btree (id);


--
-- Name: ix_uploaded_files_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_uploaded_files_ref ON public.uploaded_files USING btree (ref_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_active ON public.users USING btree ("tenantId", "isActive");


--
-- Name: ix_users_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_created ON public.users USING btree ("tenantId", "createdAt");


--
-- Name: ix_users_tenant_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_tenant_email ON public.users USING btree ("tenantId", email);


--
-- Name: ix_users_tenant_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_phone ON public.users USING btree ("tenantId", phone);


--
-- Name: ix_users_tenant_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_role ON public.users USING btree ("tenantId", role);


--
-- Name: source_credentials source_credentials_source_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_credentials
    ADD CONSTRAINT source_credentials_source_config_id_fkey FOREIGN KEY (source_config_id) REFERENCES public.source_configs(id);


--
-- PostgreSQL database dump complete
--

\unrestrict UU7oOx8q7XC9yeJDj3797kAh5UWVcYCZf4uQPd9IUjGeDVRdpb0Ml2oZpKdQN5V

