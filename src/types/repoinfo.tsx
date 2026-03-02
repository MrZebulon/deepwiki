export interface RepoInfo {
    owner: string;
    repo: string;
    type: string;
    token: string | null;
    localPath: string | null;
    repoUrl: string | null;
    branch?: string | null;
    commit?: string | null;
}

export default RepoInfo;