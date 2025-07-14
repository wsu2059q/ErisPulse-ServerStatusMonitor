import time
import asyncio
from ErisPulse import sdk

class Main:
    def __init__(self, sdk):
        self.sdk = sdk
        self.logger = sdk.logger
        self.adapter = sdk.adapter
        
        self._register_handlers()
    
    @staticmethod
    def should_eager_load() -> bool:
        return True
    def _register_handlers(self):
        self.adapter.on("message")(self._handle_message)
        self.logger.info("ServerStatusMonitor 模块已注册事件处理程序")

    async def _handle_message(self, data):
        if data.get("alt_message"):
            text = data.get("alt_message", "").strip()
            if text.strip().lower() in ["/服务器状态", "服务器状态", "/status"]:
                await self._send_status(data)
            return
        else:
            return
            
    async def _send_status(self, data):
        try:
            status = sdk.SystemStatus.get()
            
            detail_type = data.get("detail_type", "private")
            detail_id = data.get("user_id") if detail_type == "private" else data.get("group_id")
            adapter_name = data.get("self", {}).get("platform", None)
            
            if adapter_name:
                adapter = getattr(self.sdk.adapter, adapter_name)
                message = self._format_status(status)
                send_to = adapter.Send.To("user" if detail_type == "private" else "group", detail_id)
                
                # 先发送 Markdown，如果不支持则为 Text
                if hasattr(send_to, 'Markdown'):
                    await send_to.Markdown(message)
                elif hasattr(send_to, 'Text'):
                    await send_to.Text(message)
                else:
                    self.logger.error(f"适配器 {adapter_name} 既不支持 Markdown 也不支持 Text 发送方法")
                    
        except Exception as e:
            self.logger.error(f"发送服务器状态失败: {e}")

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
