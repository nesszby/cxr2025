from base.parser import Parser
import time
import hashlib
import random
import requests
import re
from typing import Dict, Optional
import urllib.parse

# 核心配置
CONFIG = {
    'upstream': [
        'http://198.16.100.186:8278/',
        'http://50.7.92.106:8278/',
        'http://50.7.234.10:8278/',
        'http://50.7.220.170:8278/',
        'http://67.159.6.34:8278/'
    ],
    'list_url': 'https://cdn.jsdelivr.net/gh/hostemail/cdn@main/data/smart.txt',
    'backup_url': 'https://cdn.jsdelivr.net/gh/hostemail/cdn@main/data/smart1.txt',
    'token_ttl': 2400,  # 40分钟有效期
    'cache_ttl': 3600,   # 频道列表缓存1小时
    'fallback': 'http://vjs.zencdn.net/v/oceans.mp4',
    'clear_key': 'leifeng'
}

class Parser(Parser):
    # 全局缓存频道列表
    _channel_cache = None
    _cache_time = None

    def parse(self, params: Dict[str, str]) -> Dict[str, str]:
        """实现抽象方法，解析参数并返回播放信息"""
        action = params.get('action')
        
        # 处理缓存清理
        if action == 'clear_cache':
            result = self.clear_cache(params)
            return {"error": result.get("error")} if result.get("error") else {"url": "cache_cleared"}
        
        # 处理频道列表请求（无id参数时）
        channel_id = params.get('id')
        if not channel_id:
            channels = self.get_channel_list()
            return {"error": channels.get("error")} if channels.get("error") else {"channels": channels.get("channels")}
        
        # 处理播放请求
        ts_file = params.get('ts')
        token = self.manage_token(params)
        try:
            if ts_file:
                # 代理TS流
                ts_data = self.proxy_ts(channel_id, ts_file, token)
                return {"error": ts_data.get("error")} if ts_data.get("error") else {
                    "url": ts_data.get("ts_data"),
                    "headers": {"Content-Type": "video/MP2T"}
                }
            else:
                # 生成M3U8
                m3u8_data = self.generate_m3u8(channel_id, token)
                return {"error": m3u8_data.get("error")} if m3u8_data.get("error") else {
                    "url": m3u8_data.get("m3u8"),
                    "headers": {"Content-Type": "application/vnd.apple.mpegurl"}
                }
        except Exception as e:
            return {"error": f"处理失败: {str(e)}"}

    def get_upstream(self) -> str:
        """轮询获取上游服务器地址"""
        upstream_index = int(time.time()) % len(CONFIG['upstream'])
        return CONFIG['upstream'][upstream_index]

    def fetch_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """带重试机制的URL请求"""
        retry_delay = 0.5
        for i in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=5,
                    verify=False,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response.text
            except Exception:
                if i == max_retries - 1:
                    return None
                time.sleep(retry_delay)
                retry_delay *= 2
        return None

    def get_channel_list(self, force_refresh: bool = False) -> Dict[str, str]:
        """获取频道列表（带缓存）"""
        current_time = time.time()
        # 检查缓存有效性
        if not force_refresh and self._channel_cache and (current_time - self._cache_time) < CONFIG['cache_ttl']:
            return {"channels": self._channel_cache}
        
        # 尝试主备数据源
        raw_data = self.fetch_with_retry(CONFIG['list_url']) or self.fetch_with_retry(CONFIG['backup_url'])
        if not raw_data:
            return {"error": "所有数据源均不可用"}
        
        # 解析频道列表
        channels = []
        current_group = '默认分组'
        for line in raw_data.splitlines():
            line = line.strip()
            if not line:
                continue
            if '#genre#' in line:
                current_group = line.replace(',#genre#', '').strip()
                continue
            name_parts = line.split(',')
            if len(name_parts) < 2:
                continue
            name = name_parts[0]
            url_params = urllib.parse.parse_qs(urllib.parse.urlparse(name_parts[1]).query)
            channel_id = url_params.get('id', [None])[0]
            if channel_id:
                channels.append({'id': channel_id, 'name': name, 'group': current_group})
        
        if not channels:
            return {"error": "频道列表解析失败"}
        
        # 更新缓存
        self._channel_cache = channels
        self._cache_time = current_time
        return {"channels": channels}

    def manage_token(self, params: Dict[str, str]) -> str:
        """生成/验证Token"""
        token = params.get('token', '')
        if self.validate_token(token):
            return token
        # 生成新Token（格式：随机32位十六进制+时间戳）
        return f"{random.getrandbits(128):032x}:{int(time.time())}"

    def validate_token(self, token: str) -> bool:
        """验证Token有效性"""
        parts = token.split(':')
        if len(parts) != 2:
            return False
        try:
            return (time.time() - int(parts[1])) <= CONFIG['token_ttl']
        except ValueError:
            return False

    def generate_m3u8(self, channel_id: str, token: str) -> Dict[str, str]:
        """生成带签名的M3U8播放列表"""
        upstream = self.get_upstream()
        ct = int(time.time() / 150)
        # 计算签名
        sign_str = f"tvata nginx auth module/{channel_id}/playlist.m3u8mc42afe745533{ct}"
        tsum = hashlib.md5(sign_str.encode()).hexdigest()
        auth_url = f"{upstream}{channel_id}/playlist.m3u8?tid=mc42afe745533&ct={ct}&tsum={tsum}"
        
        try:
            response = requests.get(auth_url, timeout=5, verify=False)
            response.raise_for_status()
            m3u8_content = response.text
        except Exception as e:
            return {"error": f"M3U8获取失败: {str(e)}"}
        
        # 替换TS链接为带Token的代理地址
        base_url = f"http://{params.get('host', '')}/" if params.get('host') else ""
        ts_pattern = r'(\S+\.ts)'
        m3u8_content = re.sub(
            ts_pattern,
            lambda m: f"{base_url}?id={channel_id}&ts={urllib.parse.quote(m.group(1))}&token={token}",
            m3u8_content
        )
        return {"m3u8": m3u8_content}

    def proxy_ts(self, channel_id: str, ts_file: str, token: str) -> Dict[str, str]:
        """代理TS流文件"""
        if not self.validate_token(token):
            return {"error": "无效的Token"}
        
        upstream = self.get_upstream()
        ts_url = f"{upstream}{channel_id}/{ts_file}"
        try:
            response = requests.get(
                ts_url,
                headers={'CLIENT-IP': '127.0.0.1', 'X-FORWARDED-FOR': '127.0.0.1'},
                timeout=10,
                verify=False,
                stream=True
            )
            response.raise_for_status()
            return {"ts_data": ts_url, "content_type": "video/MP2T"}  # 返回TS原始URL而非二进制内容
        except Exception as e:
            return {"error": f"TS代理失败: {str(e)}"}

    def clear_cache(self, params: Dict[str, str]) -> Dict[str, str]:
        """清除频道列表缓存"""
        key = params.get('key', '')
        client_ip = params.get('ip', 'unknown')
        if client_ip not in ['127.0.0.1', '::1'] and key != CONFIG['clear_key']:
            return {"error": "权限验证失败"}
        
        self._channel_cache = None
        self._cache_time = 0
        self.get_channel_list(force_refresh=True)
        return {"status": "缓存已清除"}

    def stop(self):
        """清理资源"""
        pass

    def proxy(self, url: str, headers: Dict[str, str]) -> Optional[bytes]:
        """代理流处理（可选实现）"""
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            return response.content
        except Exception:
            return None
