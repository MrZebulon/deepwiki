'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { FaWikipediaW, FaGithub, FaCoffee, FaTwitter } from 'react-icons/fa';
import ThemeToggle from '@/components/theme-toggle';
import ConfigurationModal from '@/components/ConfigurationModal';
import ProcessedProjects from '@/components/ProcessedProjects';
import { extractUrlPath, extractUrlDomain } from '@/utils/urlDecoder';
import { useProcessedProjects } from '@/hooks/useProcessedProjects';

import { useLanguage } from '@/contexts/LanguageContext';

export default function Home() {
  const router = useRouter();
  const { language, setLanguage, messages, supportedLanguages } = useLanguage();
  const { projects, isLoading: projectsLoading } = useProcessedProjects();

  // Create a simple translation function
  const t = (key: string, params: Record<string, string | number> = {}): string => {
    // Split the key by dots to access nested properties
    const keys = key.split('.');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = messages;

    // Navigate through the nested properties
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        // Return the key if the translation is not found
        return key;
      }
    }

    // If the value is a string, replace parameters
    if (typeof value === 'string') {
      return Object.entries(params).reduce((acc: string, [paramKey, paramValue]) => {
        return acc.replace(`{${paramKey}}`, String(paramValue));
      }, value);
    }

    // Return the key if the value is not a string
    return key;
  };

  const [repositoryInput, setRepositoryInput] = useState('https://github.com/AsyncFuncAI/deepwiki-open');

  const REPO_CONFIG_CACHE_KEY = 'deepwikiRepoConfigCache';

  const loadConfigFromCache = (repoUrl: string) => {
    if (!repoUrl) return;
    try {
      const cachedConfigs = localStorage.getItem(REPO_CONFIG_CACHE_KEY);
      if (cachedConfigs) {
        const configs = JSON.parse(cachedConfigs);
        const config = configs[repoUrl.trim()];
        if (config) {
          setSelectedLanguage(config.selectedLanguage || language);
          setIsComprehensiveView(config.isComprehensiveView === undefined ? true : config.isComprehensiveView);
          setProvider(config.provider || '');
          setModel(config.model || '');
          setIsCustomModel(config.isCustomModel || false);
          setCustomModel(config.customModel || '');
          setEmbedderProvider(config.embedderProvider || '');
          setEmbedderModel(config.embedderModel || '');
          setSelectedPlatform(config.selectedPlatform || 'github');
          setSelectedBranch(config.selectedBranch || '');
          setSelectedCommit(config.selectedCommit || '');
          setExcludedDirs(config.excludedDirs || '');
          setExcludedFiles(config.excludedFiles || '');
          setIncludedDirs(config.includedDirs || '');
          setIncludedFiles(config.includedFiles || '');
        }
      }
    } catch (error) {
      console.error('Error loading config from localStorage:', error);
    }
  };

  const handleRepositoryInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newRepoUrl = e.target.value;
    setRepositoryInput(newRepoUrl);
    if (newRepoUrl.trim() === "") {
      // Optionally reset fields if input is cleared
    } else {
        loadConfigFromCache(newRepoUrl);
    }
  };

  useEffect(() => {
    if (repositoryInput) {
      loadConfigFromCache(repositoryInput);
    }
  }, []);

  // Provider-based model selection state
  const [provider, setProvider] = useState<string>('');
  const [model, setModel] = useState<string>('');
  const [isCustomModel, setIsCustomModel] = useState<boolean>(false);
  const [customModel, setCustomModel] = useState<string>('');
  const [embedderProvider, setEmbedderProvider] = useState<string>('');
  const [embedderModel, setEmbedderModel] = useState<string>('');

  // Wiki type state - default to comprehensive view
  const [isComprehensiveView, setIsComprehensiveView] = useState<boolean>(true);

  const [excludedDirs, setExcludedDirs] = useState('');
  const [excludedFiles, setExcludedFiles] = useState('');
  const [includedDirs, setIncludedDirs] = useState('');
  const [includedFiles, setIncludedFiles] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<'github' | 'gitlab' | 'bitbucket'>('github');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedCommit, setSelectedCommit] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>(language);

  // Authentication state
  const [authRequired, setAuthRequired] = useState<boolean>(false);
  const [authCode, setAuthCode] = useState<string>('');
  const [isAuthLoading, setIsAuthLoading] = useState<boolean>(true);

  // Sync the language context with the selectedLanguage state
  useEffect(() => {
    setLanguage(selectedLanguage);
  }, [selectedLanguage, setLanguage]);

  // Fetch authentication status on component mount
  useEffect(() => {
    const fetchAuthStatus = async () => {
      try {
        setIsAuthLoading(true);
        const response = await fetch('/api/auth/status');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setAuthRequired(data.auth_required);
      } catch (err) {
        console.error("Failed to fetch auth status:", err);
        // Assuming auth is required if fetch fails to avoid blocking UI for safety
        setAuthRequired(true);
      } finally {
        setIsAuthLoading(false);
      }
    };

    fetchAuthStatus();
  }, []);

  // Parse repository URL/input and extract owner and repo
  const parseRepositoryInput = (input: string): {
    owner: string,
    repo: string,
    type: string,
    fullPath?: string,
    localPath?: string
  } | null => {
    input = input.trim();

    let owner = '', repo = '', type = 'github', fullPath;
    let localPath: string | undefined;

    // Handle Windows absolute paths (e.g., C:\path\to\folder)
    const windowsPathRegex = /^[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*$/;
    const customGitRegex = /^(?:https?:\/\/)?([^\/]+)\/(.+?)\/([^\/]+)(?:\.git)?\/?$/;

    if (windowsPathRegex.test(input)) {
      type = 'local';
      localPath = input;
      repo = input.split('\\').pop() || 'local-repo';
      owner = 'local';
    }
    // Handle Unix/Linux absolute paths (e.g., /path/to/folder)
    else if (input.startsWith('/')) {
      type = 'local';
      localPath = input;
      repo = input.split('/').filter(Boolean).pop() || 'local-repo';
      owner = 'local';
    }
    else if (customGitRegex.test(input)) {
      // Detect repository type based on domain
      const domain = extractUrlDomain(input);
      if (domain?.includes('github.com')) {
        type = 'github';
      } else if (domain?.includes('gitlab.com') || domain?.includes('gitlab.')) {
        type = 'gitlab';
      } else if (domain?.includes('bitbucket.org') || domain?.includes('bitbucket.')) {
        type = 'bitbucket';
      } else {
        type = 'web'; // fallback for other git hosting services
      }

      fullPath = extractUrlPath(input)?.replace(/\.git$/, '');
      const parts = fullPath?.split('/') ?? [];
      if (parts.length >= 2) {
        repo = parts[parts.length - 1] || '';
        owner = parts[parts.length - 2] || '';
      }
    }
    // Unsupported URL formats
    else {
      console.error('Unsupported URL format:', input);
      return null;
    }

    if (!owner || !repo) {
      return null;
    }

    // Clean values
    owner = owner.trim();
    repo = repo.trim();

    // Remove .git suffix if present
    if (repo.endsWith('.git')) {
      repo = repo.slice(0, -4);
    }

    return { owner, repo, type, fullPath, localPath };
  };

  // State for configuration modal
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Parse repository input to validate
    const parsedRepo = parseRepositoryInput(repositoryInput);

    if (!parsedRepo) {
      setError('Invalid repository format. Use "owner/repo", GitHub/GitLab/BitBucket URL, or a local folder path like "/path/to/folder" or "C:\\path\\to\\folder".');
      return;
    }

    // If valid, open the configuration modal
    setError(null);
    setIsConfigModalOpen(true);
  };

  const validateAuthCode = async () => {
    try {
      if(authRequired) {
        if(!authCode) {
          return false;
        }
        const response = await fetch('/api/auth/validate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({'code': authCode})
        });
        if (!response.ok) {
          return false;
        }
        const data = await response.json();
        return data.success || false;
      }
    } catch {
      return false;
    }
    return true;
  };

  const handleGenerateWiki = async () => {

    // Check authorization code
    const validation = await validateAuthCode();
    if(!validation) {
      setError(`Failed to validate the authorization code`);
      console.error(`Failed to validate the authorization code`);
      setIsConfigModalOpen(false);
      return;
    }

    // Prevent multiple submissions
    if (isSubmitting) {
      console.log('Form submission already in progress, ignoring duplicate click');
      return;
    }

    try {
      const currentRepoUrl = repositoryInput.trim();
      if (currentRepoUrl) {
        const existingConfigs = JSON.parse(localStorage.getItem(REPO_CONFIG_CACHE_KEY) || '{}');
        const configToSave = {
          selectedLanguage,
          isComprehensiveView,
          provider,
          model,
          isCustomModel,
          customModel,
          embedderProvider,
          embedderModel,
          selectedPlatform,
          selectedBranch,
          selectedCommit,
          excludedDirs,
          excludedFiles,
          includedDirs,
          includedFiles,
        };
        existingConfigs[currentRepoUrl] = configToSave;
        localStorage.setItem(REPO_CONFIG_CACHE_KEY, JSON.stringify(existingConfigs));
      }
    } catch (error) {
      console.error('Error saving config to localStorage:', error);
    }

    setIsSubmitting(true);

    // Parse repository input
    const parsedRepo = parseRepositoryInput(repositoryInput);

    if (!parsedRepo) {
      setError('Invalid repository format. Use "owner/repo", GitHub/GitLab/BitBucket URL, or a local folder path like "/path/to/folder" or "C:\\path\\to\\folder".');
      setIsSubmitting(false);
      return;
    }

    const { owner, repo, type, localPath } = parsedRepo;

    // Store tokens in query params if they exist
    const params = new URLSearchParams();
    if (accessToken) {
      params.append('token', accessToken);
    }

    if (selectedBranch.trim()) {
      params.append('branch', selectedBranch.trim());
    }
    if (selectedCommit.trim()) {
      params.append('commit', selectedCommit.trim());
    }

    // Always include the type parameter
    params.append('type', (type == 'local' ? type : selectedPlatform) || 'github');
    // Add local path if it exists
    if (localPath) {
      params.append('local_path', encodeURIComponent(localPath));
    } else {
      params.append('repo_url', encodeURIComponent(repositoryInput));
    }
    // Add model parameters
    params.append('provider', provider);
    params.append('model', model);
    if (embedderProvider) {
      params.append('embedder_provider', embedderProvider);
    }
    if (embedderModel) {
      params.append('embedder_model', embedderModel);
    }
    if (isCustomModel && customModel) {
      params.append('custom_model', customModel);
    }
    // Add file filters configuration
    if (excludedDirs) {
      params.append('excluded_dirs', excludedDirs);
    }
    if (excludedFiles) {
      params.append('excluded_files', excludedFiles);
    }
    if (includedDirs) {
      params.append('included_dirs', includedDirs);
    }
    if (includedFiles) {
      params.append('included_files', includedFiles);
    }

    // Add language parameter
    params.append('language', selectedLanguage);

    // Add comprehensive parameter
    params.append('comprehensive', isComprehensiveView.toString());

    const queryString = params.toString() ? `?${params.toString()}` : '';

    // Navigate to the dynamic route
    router.push(`/${owner}/${repo}${queryString}`);

    // The isSubmitting state will be reset when the component unmounts during navigation
  };

  const quickExamples = [
    'https://github.com/AsyncFuncAI/deepwiki-open',
    'https://gitlab.com/gitlab-org/gitlab',
    'AsyncFuncAI/deepwiki-open',
    'https://bitbucket.org/atlassian/atlaskit',
  ];

  return (
    <div className="min-h-screen paper-texture px-4 py-5 md:px-8 md:py-7">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <header className="w-full">
          <div className="flex items-center justify-between bg-[var(--card-bg)]/95 rounded-2xl border border-[var(--border-color)] shadow-custom px-4 py-3 md:px-5">
            <div className="flex items-center gap-3">
              <div className="bg-[var(--accent-primary)] p-2 rounded-lg">
                <FaWikipediaW className="text-xl text-white" />
              </div>
              <div>
                <h1 className="text-lg md:text-xl font-bold text-[var(--foreground)]">{t('common.appName')}</h1>
                <p className="text-xs text-[var(--muted)]">{t('common.tagline')}</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Link href="/wiki/projects" className="text-sm text-[var(--accent-primary)] hover:underline">
                {t('nav.wikiProjects')}
              </Link>
              <Link href="/settings" className="text-sm text-[var(--accent-primary)] hover:underline">
                Settings
              </Link>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main className="w-full flex flex-col gap-6">
          <section className="bg-[var(--card-bg)] rounded-2xl border border-[var(--border-color)] shadow-custom px-5 py-8 md:px-10 md:py-12">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/20 text-xs text-[var(--accent-primary)] mb-5">
                AI Wiki for Code Repositories
              </div>

              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-[var(--foreground)] mb-4">
                Understand any codebase in minutes.
              </h2>
              <p className="text-sm md:text-base text-[var(--muted)] max-w-2xl mx-auto mb-8 leading-relaxed">
                {t('home.description')}
              </p>

              <form onSubmit={handleFormSubmit} className="w-full max-w-3xl mx-auto">
                <div className="flex flex-col md:flex-row gap-3 md:items-center">
                  <input
                    type="text"
                    value={repositoryInput}
                    onChange={handleRepositoryInputChange}
                    placeholder={t('form.repoPlaceholder') || 'owner/repo, GitHub/GitLab/BitBucket URL, or local folder path'}
                    className="input-japanese flex-1 px-4 py-3 rounded-xl border-[var(--border-color)] bg-[var(--background)]/60 text-[var(--foreground)] focus:border-[var(--accent-primary)]"
                  />
                  <button
                    type="submit"
                    className="btn-japanese px-7 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? t('common.processing') : t('common.generateWiki')}
                  </button>
                </div>
                {error && (
                  <p className="text-left text-[var(--highlight)] text-xs mt-2">{error}</p>
                )}
              </form>

              <div className="mt-6 text-left max-w-3xl mx-auto">
                <p className="text-xs text-[var(--muted)] mb-2">{t('home.enterRepoUrl')}</p>
                <div className="flex flex-wrap gap-2">
                  {quickExamples.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => {
                        setRepositoryInput(example);
                        loadConfigFromCache(example);
                      }}
                      className="px-3 py-1.5 text-xs rounded-full border border-[var(--border-color)] bg-[var(--background)]/70 text-[var(--foreground)] hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)] transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {!projectsLoading && projects.length > 0 ? (
            <section className="bg-[var(--card-bg)] rounded-2xl border border-[var(--border-color)] shadow-custom p-5 md:p-7">
              <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5">
                <div>
                  <h3 className="text-xl font-semibold text-[var(--foreground)]">{t('projects.existingProjects')}</h3>
                  <p className="text-sm text-[var(--muted)]">{t('projects.browseExisting')}</p>
                </div>
                <Link href="/wiki/projects" className="text-sm text-[var(--accent-primary)] hover:underline">
                  {t('nav.wikiProjects')}
                </Link>
              </div>
              <ProcessedProjects showHeader={false} maxItems={6} messages={messages} className="w-full" />
            </section>
          ) : (
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] shadow-custom p-5">
                <p className="text-xs text-[var(--accent-primary)] mb-2">01</p>
                <h3 className="text-base font-semibold text-[var(--foreground)] mb-2">Paste repository URL</h3>
                <p className="text-sm text-[var(--muted)]">GitHub, GitLab, Bitbucket, and local paths are supported.</p>
              </div>
              <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] shadow-custom p-5">
                <p className="text-xs text-[var(--accent-primary)] mb-2">02</p>
                <h3 className="text-base font-semibold text-[var(--foreground)] mb-2">Pick your model</h3>
                <p className="text-sm text-[var(--muted)]">Configure provider, model, language, and optional file filters.</p>
              </div>
              <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] shadow-custom p-5">
                <p className="text-xs text-[var(--accent-primary)] mb-2">03</p>
                <h3 className="text-base font-semibold text-[var(--foreground)] mb-2">Explore generated wiki</h3>
                <p className="text-sm text-[var(--muted)]">Review pages, diagrams, and ask follow-up questions about code.</p>
              </div>
            </section>
          )}
        </main>

        <footer className="w-full">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-[var(--card-bg)] rounded-2xl p-4 border border-[var(--border-color)] shadow-custom">
            <p className="text-[var(--muted)] text-sm">{t('footer.copyright')}</p>
            <div className="flex items-center gap-5">
              <a href="https://github.com/AsyncFuncAI/deepwiki-open" target="_blank" rel="noopener noreferrer" className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors">
                <FaGithub className="text-xl" />
              </a>
              <a href="https://buymeacoffee.com/sheing" target="_blank" rel="noopener noreferrer" className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors">
                <FaCoffee className="text-xl" />
              </a>
              <a href="https://x.com/sashimikun_void" target="_blank" rel="noopener noreferrer" className="text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors">
                <FaTwitter className="text-xl" />
              </a>
            </div>
          </div>
        </footer>

        <ConfigurationModal
          isOpen={isConfigModalOpen}
          onClose={() => setIsConfigModalOpen(false)}
          repositoryInput={repositoryInput}
          selectedLanguage={selectedLanguage}
          setSelectedLanguage={setSelectedLanguage}
          supportedLanguages={supportedLanguages}
          isComprehensiveView={isComprehensiveView}
          setIsComprehensiveView={setIsComprehensiveView}
          provider={provider}
          setProvider={setProvider}
          model={model}
          setModel={setModel}
          isCustomModel={isCustomModel}
          setIsCustomModel={setIsCustomModel}
          customModel={customModel}
          setCustomModel={setCustomModel}
          embedderProvider={embedderProvider}
          setEmbedderProvider={setEmbedderProvider}
          embedderModel={embedderModel}
          setEmbedderModel={setEmbedderModel}
          selectedPlatform={selectedPlatform}
          setSelectedPlatform={setSelectedPlatform}
          accessToken={accessToken}
          setAccessToken={setAccessToken}
          selectedBranch={selectedBranch}
          setSelectedBranch={setSelectedBranch}
          selectedCommit={selectedCommit}
          setSelectedCommit={setSelectedCommit}
          excludedDirs={excludedDirs}
          setExcludedDirs={setExcludedDirs}
          excludedFiles={excludedFiles}
          setExcludedFiles={setExcludedFiles}
          includedDirs={includedDirs}
          setIncludedDirs={setIncludedDirs}
          includedFiles={includedFiles}
          setIncludedFiles={setIncludedFiles}
          onSubmit={handleGenerateWiki}
          isSubmitting={isSubmitting}
          authRequired={authRequired}
          authCode={authCode}
          setAuthCode={setAuthCode}
          isAuthLoading={isAuthLoading}
        />
      </div>
    </div>
  );
}