import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import * as crypto from "crypto";

const DEFAULT_API_BASE = "https://t0ken.ai/api";

const PLUGIN_DIR = path.join(os.homedir(), ".openclaw", "extensions", "memoryx-openclaw-plugin");

let logStream: fs.WriteStream | null = null;
let logStreamReady = false;

function ensureDir(): void {
    if (!fs.existsSync(PLUGIN_DIR)) {
        fs.mkdirSync(PLUGIN_DIR, { recursive: true });
    }
}

function log(message: string): void {
    console.log(`[MemoryX] ${message}`);
    setImmediate(() => {
        try {
            if (!logStreamReady) {
                ensureDir();
                logStream = fs.createWriteStream(path.join(PLUGIN_DIR, "plugin.log"), { flags: "a" });
                logStreamReady = true;
            }
            logStream?.write(`[${new Date().toISOString()}] ${message}\n`);
        } catch (e) {
            // ignore
        }
    });
}

interface PluginConfig {
    apiBaseUrl?: string;
}

interface MemoryXConfig {
    apiKey: string | null;
    projectId: string;
    userId: string | null;
    initialized: boolean;
    apiBaseUrl: string;
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

class JsonStorage {
    private static configPath: string | null = null;
    
    private static getPath(): string {
        if (!this.configPath) {
            ensureDir();
            this.configPath = path.join(PLUGIN_DIR, "config.json");
        }
        return this.configPath;
    }
    
    static load(): MemoryXConfig | null {
        try {
            const filePath = this.getPath();
            if (fs.existsSync(filePath)) {
                const data = fs.readFileSync(filePath, "utf-8");
                return JSON.parse(data);
            }
        } catch (e) {
            console.warn("[MemoryX] Failed to load config:", e);
        }
        return null;
    }
    
    static save(config: MemoryXConfig): void {
        try {
            const filePath = this.getPath();
            fs.writeFileSync(filePath, JSON.stringify(config, null, 2), "utf-8");
        } catch (e) {
            console.warn("[MemoryX] Failed to save config:", e);
        }
    }
}

class ConversationBuffer {
    private messages: Message[] = [];
    private roundCount: number = 0;
    private lastRole: string = "";
    private conversationId: string = "";
    private startedAt: number = Date.now();
    private lastActivityAt: number = Date.now();
    
    private readonly ROUND_THRESHOLD = 2;
    private readonly TIMEOUT_MS = 30 * 60 * 1000;
    
    constructor() {
        this.conversationId = this.generateId();
    }
    
    private generateId(): string {
        return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    addMessage(role: string, content: string): boolean {
        if (!content || content.length < 2) {
            return false;
        }
        
        const message: Message = {
            role,
            content,
            tokens: 0,
            timestamp: Date.now()
        };
        
        this.messages.push(message);
        this.lastActivityAt = Date.now();
        
        if (role === "assistant" && this.lastRole === "user") {
            this.roundCount++;
        }
        this.lastRole = role;
        
        return this.roundCount >= this.ROUND_THRESHOLD;
    }
    
    shouldFlush(): boolean {
        if (this.messages.length === 0) {
            return false;
        }
        
        if (this.roundCount >= this.ROUND_THRESHOLD) {
            return true;
        }
        
        const elapsed = Date.now() - this.lastActivityAt;
        if (elapsed > this.TIMEOUT_MS) {
            return true;
        }
        
        return false;
    }
    
    flush(): { conversation_id: string; messages: Message[] } {
        const data = {
            conversation_id: this.conversationId,
            messages: [...this.messages]
        };
        
        this.messages = [];
        this.roundCount = 0;
        this.lastRole = "";
        this.conversationId = this.generateId();
        this.startedAt = Date.now();
        this.lastActivityAt = Date.now();
        
        return data;
    }
    
    forceFlush(): { conversation_id: string; messages: Message[] } | null {
        if (this.messages.length === 0) {
            return null;
        }
        return this.flush();
    }
    
    getStatus(): { messageCount: number; conversationId: string } {
        return {
            messageCount: this.messages.length,
            conversationId: this.conversationId
        };
    }
}

class MemoryXPlugin {
    private config: MemoryXConfig = {
        apiKey: null,
        projectId: "default",
        userId: null,
        initialized: false,
        apiBaseUrl: DEFAULT_API_BASE
    };
    
    private buffer: ConversationBuffer = new ConversationBuffer();
    private flushTimer: any = null;
    private readonly FLUSH_CHECK_INTERVAL = 30000;
    private pluginConfig: PluginConfig | null = null;
    private initialized: boolean = false;
    
    constructor(pluginConfig?: PluginConfig) {
        this.pluginConfig = pluginConfig || null;
        if (pluginConfig?.apiBaseUrl) {
            this.config.apiBaseUrl = pluginConfig.apiBaseUrl;
        }
        this.config.initialized = true;
    }
    
    init(): void {
        if (this.initialized) return;
        this.initialized = true;
        
        log("Async init started");
        this.loadConfig();
        log(`Config loaded, apiKey: ${this.config.apiKey ? 'present' : 'missing'}`);
        this.startFlushTimer();
        
        if (!this.config.apiKey) {
            log("Starting auto-register");
            this.autoRegister().catch(e => log(`Auto-register failed: ${e}`));
        }
    }
    
    private get apiBase(): string {
        return this.config.apiBaseUrl || DEFAULT_API_BASE;
    }
    
    private loadConfig(): void {
        const stored = JsonStorage.load();
        if (stored) {
            this.config = { 
                ...this.config, 
                ...stored,
                apiBaseUrl: this.pluginConfig?.apiBaseUrl || stored.apiBaseUrl || this.config.apiBaseUrl
            };
        }
    }
    
    private saveConfig(): void {
        JsonStorage.save(this.config);
    }
    
    private async autoRegister(): Promise<void> {
        try {
            const fingerprint = this.getMachineFingerprint();
            
            const response = await fetch(`${this.apiBase}/agents/auto-register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    machine_fingerprint: fingerprint,
                    agent_type: "openclaw",
                    agent_name: "openclaw-agent",
                    platform: os.platform(),
                    platform_version: os.release()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Auto-register failed: ${response.status}`);
            }
            
            const data: any = await response.json();
            this.config.apiKey = data.api_key;
            this.config.projectId = String(data.project_id);
            this.config.userId = data.agent_id;
            this.saveConfig();
            
            log("Auto-registered successfully");
        } catch (e) {
            log(`Auto-register failed: ${e}`);
        }
    }
    
    private getMachineFingerprint(): string {
        const components = [
            os.hostname(),
            os.platform(),
            os.arch(),
            os.cpus()[0]?.model || "unknown",
            os.totalmem()
        ];
        
        const raw = components.join("|");
        return crypto.createHash("sha256").update(raw).digest("hex").slice(0, 32);
    }
    
    private startFlushTimer(): void {
        this.flushTimer = setInterval(() => {
            if (this.buffer.shouldFlush()) {
                this.flushConversation();
            }
        }, this.FLUSH_CHECK_INTERVAL);
    }
    
    private async flushConversation(): Promise<void> {
        if (!this.config.apiKey) {
            return;
        }
        
        const data = this.buffer.forceFlush();
        if (!data || data.messages.length === 0) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/v1/conversations/flush`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": this.config.apiKey
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const errorData: any = await response.json().catch(() => ({}));
                
                if (response.status === 402) {
                    log(`Quota exceeded: ${errorData.detail}`);
                } else {
                    log(`Flush failed: ${JSON.stringify(errorData)}`);
                }
            } else {
                const result: any = await response.json();
                log(`Flushed ${data.messages.length} messages, extracted ${result.extracted_count} memories`);
            }
        } catch (e) {
            log(`Flush error: ${e}`);
        }
    }
    
    public async onMessage(role: string, content: string): Promise<boolean> {
        this.init();
        
        if (!content || content.length < 2) {
            return false;
        }
        
        const skipPatterns = [
            /^[好的ok谢谢嗯啊哈哈你好hihello拜拜再见]{1,5}$/i,
            /^[？?！!。,，\s]{1,10}$/
        ];
        
        for (const pattern of skipPatterns) {
            if (pattern.test(content.trim())) {
                return false;
            }
        }
        
        const shouldFlush = this.buffer.addMessage(role, content);
        
        if (shouldFlush) {
            await this.flushConversation();
        }
        
        return true;
    }
    
    public async recall(query: string, limit: number = 5): Promise<RecallResult> {
        this.init();
        
        if (!this.config.apiKey || !query || query.length < 2) {
            return { memories: [], isLimited: false, remainingQuota: 0 };
        }
        
        try {
            const response = await fetch(`${this.apiBase}/v1/memories/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": this.config.apiKey
                },
                body: JSON.stringify({
                    query,
                    project_id: this.config.projectId,
                    limit
                })
            });
            
            if (!response.ok) {
                const errorData: any = await response.json().catch(() => ({}));
                
                if (response.status === 402 || response.status === 429) {
                    return {
                        memories: [],
                        isLimited: true,
                        remainingQuota: 0,
                        upgradeHint: errorData.detail || "云端查询配额已用尽，请升级到付费版"
                    };
                }
                
                throw new Error(`Search failed: ${response.status}`);
            }
            
            const data: any = await response.json();
            
            return {
                memories: (data.data || []).map((m: any) => ({
                    id: m.id,
                    content: m.content,
                    category: m.category || "other",
                    score: m.score || 0.5
                })),
                isLimited: false,
                remainingQuota: data.remaining_quota ?? -1
            };
        } catch (e) {
            log(`Recall failed: ${e}`);
            return { memories: [], isLimited: false, remainingQuota: 0 };
        }
    }
    
    public async endConversation(): Promise<void> {
        await this.flushConversation();
        log("Conversation ended, buffer flushed");
    }
    
    public getStatus(): { 
        initialized: boolean; 
        hasApiKey: boolean; 
        bufferStatus: { messageCount: number; conversationId: string } 
    } {
        return {
            initialized: this.config.initialized,
            hasApiKey: !!this.config.apiKey,
            bufferStatus: this.buffer.getStatus()
        };
    }
}

let plugin: MemoryXPlugin;

export default {
    id: "memoryx-openclaw-plugin",
    name: "MemoryX Realtime Plugin",
    version: "1.2.0",
    description: "Real-time memory capture and recall for OpenClaw",
    
    register(api: any, pluginConfig?: PluginConfig): void {
        api.logger.info("[MemoryX] Plugin registering...");
        
        if (pluginConfig?.apiBaseUrl) {
            api.logger.info(`[MemoryX] API Base: \`${pluginConfig.apiBaseUrl}\``);
        }
        
        plugin = new MemoryXPlugin(pluginConfig);
        
        api.on("message_received", async (event: any, ctx: any) => {
            const { content } = event;
            if (content && plugin) {
                await plugin.onMessage("user", content);
            }
        });
        
        api.on("assistant_response", async (event: any, ctx: any) => {
            const { content } = event;
            if (content && plugin) {
                await plugin.onMessage("assistant", content);
            }
        });
        
        api.on("before_agent_start", async (event: any, ctx: any) => {
            const { prompt } = event;
            if (!prompt || prompt.length < 2 || !plugin) return;
            
            try {
                const result = await plugin.recall(prompt, 5);
                
                if (result.isLimited) {
                    api.logger.warn(`[MemoryX] ${result.upgradeHint}`);
                    return {
                        prependContext: `[系统提示] ${result.upgradeHint}\n`
                    };
                }
                
                if (result.memories.length === 0) return;
                
                const memories = result.memories
                    .map(m => `- [${m.category}] ${m.content}`)
                    .join("\n");
                
                api.logger.info(`[MemoryX] Recalled ${result.memories.length} memories from cloud`);
                
                return {
                    prependContext: `[相关记忆]\n${memories}\n[End of memories]\n`
                };
            } catch (error) {
                api.logger.warn(`[MemoryX] Recall failed: ${error}`);
            }
        });
        
        api.on("conversation_end", async (event: any, ctx: any) => {
            if (plugin) {
                await plugin.endConversation();
            }
        });
        
        api.logger.info("[MemoryX] Plugin registered successfully");
    }
};

export { MemoryXPlugin, ConversationBuffer };
