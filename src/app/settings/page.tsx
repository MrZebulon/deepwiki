'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

type RuntimeSettings = {
  provider_keys: {
    openai: { apiKey: string; baseUrl: string };
    google: { apiKey: string };
    openrouter: { apiKey: string };
    azure: { apiKey: string; endpoint: string; apiVersion: string };
    dashscope: { apiKey: string; workspaceId: string; baseUrl: string };
    bedrock: {
      accessKeyId: string;
      secretAccessKey: string;
      sessionToken: string;
      region: string;
      roleArn: string;
      profile: string;
    };
  };
  embedder: { type: string };
  auth: { enabled: boolean; code: string };
  local: { ollamaHost: string; mlxHost: string };
};

const emptySettings: RuntimeSettings = {
  provider_keys: {
    openai: { apiKey: '', baseUrl: 'https://api.openai.com/v1' },
    google: { apiKey: '' },
    openrouter: { apiKey: '' },
    azure: { apiKey: '', endpoint: '', apiVersion: '' },
    dashscope: { apiKey: '', workspaceId: '', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
    bedrock: {
      accessKeyId: '',
      secretAccessKey: '',
      sessionToken: '',
      region: 'us-east-1',
      roleArn: '',
      profile: '',
    },
  },
  embedder: { type: 'openai' },
  auth: { enabled: false, code: '' },
  local: { ollamaHost: 'http://localhost:11434', mlxHost: 'http://localhost:8080' },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings>(emptySettings);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch('/api/provider-keys', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`Failed to load settings (${response.status})`);
        }
        const data = await response.json();
        setSettings(data);
      } catch (e) {
        console.error(e);
        setError('Failed to load settings.');
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, []);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setMessage(null);
      setError(null);

      const response = await fetch('/api/provider-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        throw new Error(`Failed to save settings (${response.status})`);
      }

      setMessage('Settings saved.');
    } catch (e) {
      console.error(e);
      setError('Failed to save settings.');
    } finally {
      setIsSaving(false);
    }
  };

  const update = (path: string[], value: string | boolean) => {
    setSettings((prev) => {
      const next: RuntimeSettings = structuredClone(prev);
      let cursor: Record<string, unknown> = next as unknown as Record<string, unknown>;
      for (let i = 0; i < path.length - 1; i++) {
        cursor = cursor[path[i]] as Record<string, unknown>;
      }
      cursor[path[path.length - 1]] = value;
      return next;
    });
  };

  if (isLoading) {
    return <div className="max-w-4xl mx-auto p-6">Loading settings...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Settings</h1>
        <Link href="/" className="text-sm text-[var(--accent-primary)] hover:underline">Back to Home</Link>
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-4 space-y-4">
        <h2 className="text-lg font-semibold">Remote Provider API Keys</h2>

        <label className="block text-sm">OpenAI API Key</label>
        <input type="password" value={settings.provider_keys.openai.apiKey} onChange={(e) => update(['provider_keys', 'openai', 'apiKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">OpenAI Base URL</label>
        <input value={settings.provider_keys.openai.baseUrl} onChange={(e) => update(['provider_keys', 'openai', 'baseUrl'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />

        <label className="block text-sm">Google API Key</label>
        <input type="password" value={settings.provider_keys.google.apiKey} onChange={(e) => update(['provider_keys', 'google', 'apiKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />

        <label className="block text-sm">OpenRouter API Key</label>
        <input type="password" value={settings.provider_keys.openrouter.apiKey} onChange={(e) => update(['provider_keys', 'openrouter', 'apiKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />

        <label className="block text-sm">Azure API Key</label>
        <input type="password" value={settings.provider_keys.azure.apiKey} onChange={(e) => update(['provider_keys', 'azure', 'apiKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">Azure Endpoint</label>
        <input value={settings.provider_keys.azure.endpoint} onChange={(e) => update(['provider_keys', 'azure', 'endpoint'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">Azure API Version</label>
        <input value={settings.provider_keys.azure.apiVersion} onChange={(e) => update(['provider_keys', 'azure', 'apiVersion'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />

        <label className="block text-sm">Dashscope API Key</label>
        <input type="password" value={settings.provider_keys.dashscope.apiKey} onChange={(e) => update(['provider_keys', 'dashscope', 'apiKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">Dashscope Workspace ID (optional)</label>
        <input value={settings.provider_keys.dashscope.workspaceId} onChange={(e) => update(['provider_keys', 'dashscope', 'workspaceId'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />

        <label className="block text-sm">AWS Access Key ID</label>
        <input value={settings.provider_keys.bedrock.accessKeyId} onChange={(e) => update(['provider_keys', 'bedrock', 'accessKeyId'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">AWS Secret Access Key</label>
        <input type="password" value={settings.provider_keys.bedrock.secretAccessKey} onChange={(e) => update(['provider_keys', 'bedrock', 'secretAccessKey'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">AWS Session Token (optional)</label>
        <input value={settings.provider_keys.bedrock.sessionToken} onChange={(e) => update(['provider_keys', 'bedrock', 'sessionToken'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">AWS Region</label>
        <input value={settings.provider_keys.bedrock.region} onChange={(e) => update(['provider_keys', 'bedrock', 'region'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
        <label className="block text-sm">AWS Role ARN (optional)</label>
        <input value={settings.provider_keys.bedrock.roleArn} onChange={(e) => update(['provider_keys', 'bedrock', 'roleArn'], e.target.value)} className="input-japanese w-full px-3 py-2 rounded-md" />
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-4 space-y-4">
        <h2 className="text-lg font-semibold">Wiki Auth</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings.auth.enabled}
            onChange={(e) => update(['auth', 'enabled'], e.target.checked)}
          />
          Require authorization code for destructive operations
        </label>
        <label className="block text-sm">Authorization Code</label>
        <input
          type="password"
          value={settings.auth.code}
          onChange={(e) => update(['auth', 'code'], e.target.value)}
          className="input-japanese w-full px-3 py-2 rounded-md"
        />
      </div>

      {message && <p className="text-sm text-green-600">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="button"
        onClick={handleSave}
        disabled={isSaving}
        className="btn-japanese px-5 py-2 rounded-lg disabled:opacity-60"
      >
        {isSaving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
