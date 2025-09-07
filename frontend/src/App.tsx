import React from 'react';
import { useAppState } from './state';
import { Container, Card, ThemeToggle } from './components/Layout';
import { ManuscriptUploader } from './components/ManuscriptUploader';
import { ReviewController } from './components/ReviewController';
import { StreamConsole } from './components/StreamConsole';
import { AgentStatusBoard } from './components/AgentStatusBoard';
import { IssuesPanel } from './components/IssuesPanel';
import { MetaPanel } from './components/MetaPanel';

const App: React.FC = () => {
    return (
        <Container>
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold tracking-tight">Systematic Review Auditor</h1>
                <ThemeToggle />
            </div>
            <Card title="Input">
                <ManuscriptUploader />
                <ReviewController />
            </Card>
            <Card title="Progress">
                <AgentStatusBoard />
                <StreamConsole />
            </Card>
            <div className="grid md:grid-cols-2 gap-4">
                <Card title="Issues"><IssuesPanel /></Card>
                <Card title="Meta-analysis"><MetaPanel /></Card>
            </div>
            <FinalJson />
        </Container>
    );
};

const FinalJson: React.FC = () => {
    const { finalResult } = useAppState() as any; // import after definition avoidance
    if (!finalResult) return null;
    return (
        <div className="rounded border bg-muted/20 p-3 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-64">
            {JSON.stringify(finalResult, null, 2)}
        </div>
    );
};

export default App;
