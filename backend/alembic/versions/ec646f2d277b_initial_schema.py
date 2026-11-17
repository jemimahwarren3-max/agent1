"""initial schema

Revision ID: ec646f2d277b
Revises: 
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ec646f2d277b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE template_category AS ENUM ('general_introduction', 'website_development', 'ai_automation', 'ai_customer_support', 'workflow_automation', 'custom_software', 'industry_specific', 'follow_up')")

    op.execute("CREATE TYPE integration_provider AS ENUM ('google_workspace')")

    op.execute("CREATE TYPE integration_status AS ENUM ('disconnected', 'connected', 'error')")

    op.execute("CREATE TYPE lead_status AS ENUM ('new', 'researched', 'qualified', 'draft_ready', 'awaiting_approval', 'approved', 'sent', 'replied', 'interested', 'meeting_requested', 'not_interested', 'unsubscribed', 'bounced', 'archived')")

    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'manager', 'member')")

    op.execute("CREATE TYPE approval_mode AS ENUM ('manual', 'automatic')")

    op.execute("CREATE TYPE campaign_stage AS ENUM ('draft', 'discovery', 'research', 'qualification', 'email_generation', 'approval', 'sending', 'monitoring', 'completed', 'paused')")

    op.execute("CREATE TYPE reply_classification AS ENUM ('interested', 'requesting_info', 'wants_meeting', 'not_interested', 'out_of_office', 'unsubscribe', 'other')")

    op.execute("CREATE TYPE lead_classification AS ENUM ('hot', 'warm', 'cold', 'unqualified')")

    op.execute("CREATE TYPE email_queue_status AS ENUM ('draft', 'awaiting_approval', 'approved', 'rejected', 'sending', 'sent', 'failed')")

    op.execute("CREATE TYPE job_status AS ENUM ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')")

    op.execute("""
    CREATE TABLE organisations (
    	name VARCHAR(255) NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id)
    )
    """)

    op.execute("""
    CREATE TABLE company_profiles (
    	organisation_id UUID NOT NULL, 
    	company_name VARCHAR(255) NOT NULL, 
    	website VARCHAR(500) NOT NULL, 
    	description VARCHAR(2000) NOT NULL, 
    	phone_numbers JSON NOT NULL, 
    	services JSON NOT NULL, 
    	target_industries JSON NOT NULL, 
    	target_markets JSON NOT NULL, 
    	outreach_messaging_notes VARCHAR(2000) NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	UNIQUE (organisation_id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE email_templates (
    	organisation_id UUID NOT NULL, 
    	name VARCHAR(255) NOT NULL, 
    	category template_category NOT NULL, 
    	subject VARCHAR(500) NOT NULL, 
    	body VARCHAR(8000) NOT NULL, 
    	is_approved BOOLEAN NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE integrations (
    	organisation_id UUID NOT NULL, 
    	provider integration_provider NOT NULL, 
    	status integration_status NOT NULL, 
    	connected_account_email VARCHAR(255), 
    	scopes JSON NOT NULL, 
    	config JSON NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE leads (
    	organisation_id UUID NOT NULL, 
    	business_name VARCHAR(255) NOT NULL, 
    	website VARCHAR(500) NOT NULL, 
    	country VARCHAR(100), 
    	city VARCHAR(100), 
    	industry VARCHAR(100), 
    	business_description VARCHAR(2000), 
    	business_email VARCHAR(255), 
    	phone_number VARCHAR(50), 
    	contact_person VARCHAR(255), 
    	contact_person_role VARCHAR(255), 
    	identified_opportunity VARCHAR(1000), 
    	recommended_service VARCHAR(255), 
    	research_notes VARCHAR(4000), 
    	status lead_status NOT NULL, 
    	last_researched_at DATE, 
    	last_contact_at DATE, 
    	next_follow_up_at DATE, 
    	is_unsubscribed BOOLEAN NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	CONSTRAINT uq_lead_org_website UNIQUE (organisation_id, website), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE suppression_list (
    	organisation_id UUID NOT NULL, 
    	email VARCHAR(255) NOT NULL, 
    	reason VARCHAR(255) NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	CONSTRAINT uq_suppression_org_email UNIQUE (organisation_id, email), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE users (
    	organisation_id UUID NOT NULL, 
    	email VARCHAR(255) NOT NULL, 
    	hashed_password VARCHAR(255) NOT NULL, 
    	full_name VARCHAR(255) NOT NULL, 
    	role user_role NOT NULL, 
    	is_active BOOLEAN NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
    )
    """)

    op.execute("""
    CREATE TABLE audit_logs (
    	organisation_id UUID NOT NULL, 
    	actor_user_id UUID, 
    	action VARCHAR(255) NOT NULL, 
    	entity_type VARCHAR(100) NOT NULL, 
    	entity_id VARCHAR(100), 
    	details JSON NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id), 
    	FOREIGN KEY(actor_user_id) REFERENCES users (id)
    )
    """)

    op.execute("""
    CREATE TABLE campaigns (
    	organisation_id UUID NOT NULL, 
    	name VARCHAR(255) NOT NULL, 
    	target_country VARCHAR(100), 
    	target_city VARCHAR(100), 
    	target_industry VARCHAR(100), 
    	lead_filters JSON NOT NULL, 
    	email_template_id UUID, 
    	integration_id UUID, 
    	max_daily_sends INTEGER NOT NULL, 
    	follow_up_interval_days INTEGER NOT NULL, 
    	approval_mode approval_mode NOT NULL, 
    	stage campaign_stage NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id), 
    	FOREIGN KEY(email_template_id) REFERENCES email_templates (id), 
    	FOREIGN KEY(integration_id) REFERENCES integrations (id)
    )
    """)

    op.execute("""
    CREATE TABLE email_replies (
    	lead_id UUID NOT NULL, 
    	gmail_thread_id VARCHAR(255) NOT NULL, 
    	gmail_message_id VARCHAR(255) NOT NULL, 
    	body_snippet VARCHAR(2000), 
    	classification reply_classification NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id), 
    	UNIQUE (gmail_message_id)
    )
    """)

    op.execute("""
    CREATE TABLE lead_scores (
    	lead_id UUID NOT NULL, 
    	score FLOAT NOT NULL, 
    	classification lead_classification NOT NULL, 
    	explanation VARCHAR(2000) NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id)
    )
    """)

    op.execute("""
    CREATE TABLE lead_sources (
    	lead_id UUID NOT NULL, 
    	source_url VARCHAR(1000) NOT NULL, 
    	field_name VARCHAR(100) NOT NULL, 
    	discovered_via VARCHAR(100) NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id)
    )
    """)

    op.execute("""
    CREATE TABLE oauth_tokens (
    	integration_id UUID NOT NULL, 
    	encrypted_access_token BYTEA, 
    	encrypted_refresh_token BYTEA, 
    	token_expiry VARCHAR(64), 
    	is_revoked BOOLEAN NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	UNIQUE (integration_id), 
    	FOREIGN KEY(integration_id) REFERENCES integrations (id)
    )
    """)

    op.execute("""
    CREATE TABLE research_reports (
    	lead_id UUID NOT NULL, 
    	crawled_urls JSON NOT NULL, 
    	extracted_data JSON NOT NULL, 
    	summary VARCHAR(4000), 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id)
    )
    """)

    op.execute("""
    CREATE TABLE campaign_leads (
    	campaign_id UUID NOT NULL, 
    	lead_id UUID NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	CONSTRAINT uq_campaign_lead UNIQUE (campaign_id, lead_id), 
    	FOREIGN KEY(campaign_id) REFERENCES campaigns (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id)
    )
    """)

    op.execute("""
    CREATE TABLE email_queue (
    	campaign_id UUID NOT NULL, 
    	lead_id UUID NOT NULL, 
    	subject VARCHAR(500) NOT NULL, 
    	body VARCHAR(8000) NOT NULL, 
    	status email_queue_status NOT NULL, 
    	reviewed_by_user_id UUID, 
    	rejection_reason VARCHAR(1000), 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(campaign_id) REFERENCES campaigns (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id), 
    	FOREIGN KEY(reviewed_by_user_id) REFERENCES users (id)
    )
    """)

    op.execute("""
    CREATE TABLE follow_up_tasks (
    	campaign_id UUID NOT NULL, 
    	lead_id UUID NOT NULL, 
    	scheduled_for DATE NOT NULL, 
    	is_approved BOOLEAN NOT NULL, 
    	is_sent BOOLEAN NOT NULL, 
    	is_cancelled BOOLEAN NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(campaign_id) REFERENCES campaigns (id), 
    	FOREIGN KEY(lead_id) REFERENCES leads (id)
    )
    """)

    op.execute("""
    CREATE TABLE scraping_jobs (
    	organisation_id UUID NOT NULL, 
    	campaign_id UUID, 
    	search_params JSON NOT NULL, 
    	status job_status NOT NULL, 
    	discovered_count INTEGER NOT NULL, 
    	researched_count INTEGER NOT NULL, 
    	failed_count INTEGER NOT NULL, 
    	duplicate_count INTEGER NOT NULL, 
    	qualified_count INTEGER NOT NULL, 
    	error_message VARCHAR(1000), 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id), 
    	FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
    )
    """)

    op.execute("""
    CREATE TABLE agent_runs (
    	organisation_id UUID NOT NULL, 
    	agent_name VARCHAR(100) NOT NULL, 
    	scraping_job_id UUID, 
    	status job_status NOT NULL, 
    	input_payload JSON NOT NULL, 
    	output_payload JSON NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(organisation_id) REFERENCES organisations (id), 
    	FOREIGN KEY(scraping_job_id) REFERENCES scraping_jobs (id)
    )
    """)

    op.execute("""
    CREATE TABLE email_logs (
    	email_queue_id UUID NOT NULL, 
    	gmail_message_id VARCHAR(255), 
    	gmail_thread_id VARCHAR(255), 
    	send_status VARCHAR(50) NOT NULL, 
    	error_message VARCHAR(1000), 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	UNIQUE (email_queue_id), 
    	FOREIGN KEY(email_queue_id) REFERENCES email_queue (id)
    )
    """)

    op.execute("""
    CREATE TABLE agent_execution_logs (
    	agent_run_id UUID NOT NULL, 
    	step_name VARCHAR(255) NOT NULL, 
    	level VARCHAR(20) NOT NULL, 
    	message VARCHAR(2000) NOT NULL, 
    	data JSON NOT NULL, 
    	id UUID NOT NULL, 
    	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    	PRIMARY KEY (id), 
    	FOREIGN KEY(agent_run_id) REFERENCES agent_runs (id)
    )
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_execution_logs CASCADE")

    op.execute("DROP TABLE IF EXISTS email_logs CASCADE")

    op.execute("DROP TABLE IF EXISTS agent_runs CASCADE")

    op.execute("DROP TABLE IF EXISTS scraping_jobs CASCADE")

    op.execute("DROP TABLE IF EXISTS follow_up_tasks CASCADE")

    op.execute("DROP TABLE IF EXISTS email_queue CASCADE")

    op.execute("DROP TABLE IF EXISTS campaign_leads CASCADE")

    op.execute("DROP TABLE IF EXISTS research_reports CASCADE")

    op.execute("DROP TABLE IF EXISTS oauth_tokens CASCADE")

    op.execute("DROP TABLE IF EXISTS lead_sources CASCADE")

    op.execute("DROP TABLE IF EXISTS lead_scores CASCADE")

    op.execute("DROP TABLE IF EXISTS email_replies CASCADE")

    op.execute("DROP TABLE IF EXISTS campaigns CASCADE")

    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")

    op.execute("DROP TABLE IF EXISTS users CASCADE")

    op.execute("DROP TABLE IF EXISTS suppression_list CASCADE")

    op.execute("DROP TABLE IF EXISTS leads CASCADE")

    op.execute("DROP TABLE IF EXISTS integrations CASCADE")

    op.execute("DROP TABLE IF EXISTS email_templates CASCADE")

    op.execute("DROP TABLE IF EXISTS company_profiles CASCADE")

    op.execute("DROP TABLE IF EXISTS organisations CASCADE")

    op.execute("DROP TYPE IF EXISTS job_status CASCADE")

    op.execute("DROP TYPE IF EXISTS integration_provider CASCADE")

    op.execute("DROP TYPE IF EXISTS lead_status CASCADE")

    op.execute("DROP TYPE IF EXISTS user_role CASCADE")

    op.execute("DROP TYPE IF EXISTS campaign_stage CASCADE")

    op.execute("DROP TYPE IF EXISTS integration_status CASCADE")

    op.execute("DROP TYPE IF EXISTS email_queue_status CASCADE")

    op.execute("DROP TYPE IF EXISTS reply_classification CASCADE")

    op.execute("DROP TYPE IF EXISTS template_category CASCADE")

    op.execute("DROP TYPE IF EXISTS lead_classification CASCADE")

    op.execute("DROP TYPE IF EXISTS approval_mode CASCADE")
