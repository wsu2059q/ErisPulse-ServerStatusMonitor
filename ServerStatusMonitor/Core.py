import time
import asyncio
from ErisPulse import sdk

class Main:
    def __init__(self, sdk):
        self.sdk = sdk
        self.logger = sdk.logger
        self.status_module = sdk.SystemStatus
        
        self._register_handlers()
        self.logger.info("ServerStatusMonitor 模块已加载")

    def _register_handlers(self):
        adapters = [
            getattr(sdk.adapter, "Yunhu", None),
            getattr(sdk.adapter, "Telegram", None),
            getattr(sdk.adapter, "OneBot", None)
        ]
        
        for adapter in adapters:
            if adapter:
                adapter.on("message")(self._handle_message)
                adapter.on("command")(self._handle_command)

    async def _handle_message(self, data):
        adapter_name = self._get_adapter_name(data)
        if not adapter_name:
            return
            
        if adapter_name == "Yunhu":
            text = data.get("event", {}).get("message", {}).get("content", {}).get("text", "").strip()
        elif adapter_name == "Telegram":
            text = data.get("text", "").strip()
        elif adapter_name == "OneBot":
            text = data.get("message", "").strip()
        else:
            return
            
        if text == "/服务器状态":
            await self._send_status(data)

    async def _handle_command(self, data):
        adapter_name = self._get_adapter_name(data)
        if not adapter_name:
            return
            
        if adapter_name == "Yunhu":
            command = data.get("event", {}).get("message", {}).get("instructionName", "").strip()
        elif adapter_name == "Telegram":
            # Telegram使用普通消息处理命令
            return
        elif adapter_name == "OneBot":
            command = data.get("raw_message", "").replace("/", "").strip()
        else:
            return
            
        if command == "服务器状态":
            await self._send_status(data)

    def _get_adapter_name(self, data):
        if not isinstance(data, dict):
            return None
            
        if "event" in data and "message" in data.get("event", {}):
            return "Yunhu"
        elif "message" in data and "chat" in data:
            return "Telegram"
        elif "message_type" in data and "message" in data:
            return "OneBot"
        return None

    async def _send_status(self, data):
        try:
            status = self.status_module.get()
            
            message = self._format_status(status)
            
            sender_info = self._get_sender_info(data)
            if not sender_info:
                return
                
            adapter_name = sender_info["adapter"]
            adapter = getattr(sdk.adapter, adapter_name)
            if adapter_name == "Yunhu":
                await adapter.Send.To(sender_info["target_type"], sender_info["target_id"]).Markdown(message)
            else:
                await adapter.Send.To(sender_info["target_type"], sender_info["target_id"]).Text(message)
        except Exception as e:
            self.logger.error(f"发送服务器状态失败: {e}")
            if sender_info:
                adapter = getattr(sdk.adapter, sender_info["adapter"])
                await adapter.Send.To(sender_info["target_type"], sender_info["target_id"]).Text("获取服务器状态失败，请稍后再试")

    def _get_sender_info(self, data):
        try:
            adapter_name = self._get_adapter_name(data)
            if not adapter_name:
                self.logger.warning("无法识别的消息平台类型")
                return None
                
            if adapter_name == "Yunhu":
                if data.get("event", {}).get("chat", {}).get("chatType", "") == "group":
                    target_type = "group"
                    target_id = data.get("event", {}).get("chat", {}).get("chatId", "")
                else:
                    target_type = "user"
                    target_id = data.get("event", {}).get("sender", {}).get("senderId", "")
                    
            elif adapter_name == "Telegram":
                if data.get("chat", {}).get("type") == "group":
                    target_type = "group"
                else:
                    target_type = "user"
                target_id = data.get("chat", {}).get("id", "")
                
            elif adapter_name == "OneBot":
                if data.get("message_type") == "group":
                    target_type = "group"
                else:
                    target_type = "user"
                target_id = data.get(f"{target_type}_id", "")
                
            return {
                "adapter": adapter_name,
                "target_type": target_type,
                "target_id": target_id
            }
            
        except Exception as e:
            self.logger.error(f"解析发送者信息失败: {e}")
            return None

    def _format_status(self, status):
        try:
            system = status.get("system", {})
            memory = status.get("memory", {})
            cpu = status.get("cpu", {})
            env = status.get("env", {})
            disk = status.get("disk", {})
            
            return f"""
**🖥️ 服务器状态报告**

**系统信息**
- 类型: {system.get('type', '未知')}
- 版本: {system.get('version', '未知')}

**硬件状态**
- CPU: {cpu.get('cores', '?')}核 {cpu.get('threads', '?')}线程 (使用率: {cpu.get('usage', '?')})
- 内存: {memory.get('used', '?')}MB / {memory.get('total', '?')}MB (使用率: {memory.get('usage', '?')})
- 磁盘: {disk.get('used', '?')} / {disk.get('total', '?')} (使用率: {disk.get('usage', '?')})

**环境信息**
- ErisPulse: {env.get('erispulse', '?')}
- Python: {env.get('python', '?')}

_更新时间: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}_
"""
        except Exception as e:
            self.logger.error(f"格式化状态信息失败: {e}")
            return "**服务器状态**\n\n无法获取系统状态信息"