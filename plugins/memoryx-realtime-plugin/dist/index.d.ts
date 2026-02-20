/**
 * MemoryX Realtime Plugin for OpenClaw - Phase 1
 *
 * Features:
 * - ConversationBuffer with token counting
 * - Batch upload to /conversations/flush
 * - Auto-register and quota handling
 * - Sensitive data filtered on server
 * - Configurable API base URL
 * - Precise token counting with tiktoken
 */
interface PluginConfig {
    apiBaseUrl?: string;
}
interface Message {
    role: string;
    content: string;
    tokens: number;
    timestamp: number;
}
interface RecallResult {
    memories: Array<{
        id: string;
        content: string;
        category: string;
        score: number;
    }>;
    isLimited: boolean;
    remainingQuota: number;
    upgradeHint?: string;
}
declare class ConversationBuffer {
    private messages;
    private tokenCount;
    private roundCount;
    private lastRole;
    private conversationId;
    private startedAt;
    private lastActivityAt;
    private encoder;
    private readonly ROUND_THRESHOLD;
    private readonly TIMEOUT_MS;
    private readonly MAX_TOKENS_PER_MESSAGE;
    constructor();
    private generateId;
    private countTokens;
    addMessage(role: string, content: string): boolean;
    shouldFlush(): boolean;
    flush(): {
        conversation_id: string;
        messages: Message[];
        total_tokens: number;
    };
    forceFlush(): {
        conversation_id: string;
        messages: Message[];
        total_tokens: number;
    } | null;
    getStatus(): {
        messageCount: number;
        tokenCount: number;
        conversationId: string;
    };
}
declare class MemoryXPlugin {
    private config;
    private buffer;
    private flushTimer;
    private readonly FLUSH_CHECK_INTERVAL;
    private pluginConfig;
    constructor(pluginConfig?: PluginConfig);
    private get apiBase();
    private init;
    private loadConfig;
    private saveConfig;
    private autoRegister;
    private getMachineFingerprint;
    private startFlushTimer;
    private flushConversation;
    onMessage(role: string, content: string): Promise<boolean>;
    recall(query: string, limit?: number): Promise<RecallResult>;
    endConversation(): Promise<void>;
    getStatus(): {
        initialized: boolean;
        hasApiKey: boolean;
        bufferStatus: {
            messageCount: number;
            tokenCount: number;
        };
    };
}
export declare function onMessage(message: string, context: Record<string, any>): Promise<{
    context: Record<string, any>;
}>;
export declare function onResponse(response: string, context: Record<string, any>): string;
export declare function register(api: any, pluginConfig?: PluginConfig): void;
export { MemoryXPlugin, ConversationBuffer };
//# sourceMappingURL=index.d.ts.map