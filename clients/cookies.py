"""
Cookie管理器

提供OilChem网站的Cookie会话管理功能。
"""

import json
import threading

import requests


class OilChemCookiesManager:
    """OilChem网站Cookie管理器"""

    def __init__(self, cookies_file: str = "cookies.json"):
        """
        初始化Cookie管理器

        Args:
            cookies_file: Cookie文件路径
        """
        self.cookies_file = cookies_file
        self.session = requests.Session()
        self._lock = threading.Lock()
        self._setup_session()

    def _setup_session(self) -> None:
        """配置会话基础参数"""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.oilchem.net/",
            }
        )

    def load_cookies(self) -> bool:
        """
        从Cookie Editor导出的JSON文件加载cookies

        Returns:
            加载成功返回True，失败返回False
        """
        with self._lock:
            try:
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    cookies_data = json.load(f)

                self.session.cookies.clear()
                cookies_loaded = 0

                for cookie in cookies_data:
                    try:
                        domain = cookie.get("domain", "")
                        if domain.startswith("."):
                            domain = domain[1:]

                        if not domain or not cookie.get("name"):
                            continue

                        cookie_obj = requests.cookies.create_cookie(
                            name=cookie["name"],
                            value=cookie["value"],
                            domain=domain,
                            path=cookie.get("path", "/"),
                            secure=cookie.get("secure", False),
                            rest={"HttpOnly": cookie.get("httpOnly", False)},
                        )
                        self.session.cookies.set_cookie(cookie_obj)
                        cookies_loaded += 1

                    except Exception as e:
                        print(f"跳过无效cookie: {cookie.get('name', 'unknown')} - {e}")
                        continue

                print(f"✅ 已从 {self.cookies_file} 加载 {cookies_loaded} 个cookies")
                return True

            except FileNotFoundError:
                print(f"❌ Cookies文件不存在: {self.cookies_file}")
                return False
            except json.JSONDecodeError:
                print(f"❌ Cookies文件格式错误: {self.cookies_file}")
                return False
            except Exception as e:
                print(f"❌ 加载cookies失败: {e}")
                return False

    def validate_session(
        self, test_url: str = "https://www.oilchem.net/25-1011-17-d80b2c132805eb10.html"
    ) -> bool:
        """
        验证会话是否有效

        Args:
            test_url: 用于测试的URL

        Returns:
            会话有效返回True，无效返回False
        """
        try:
            print("🔍 验证cookies有效性...")
            response = self.session.get(test_url, timeout=10)
            response.encoding = "utf-8"

            if "立即登录" in response.text:
                print("❌ Cookies已失效：检测到'立即登录'提示")
                return False
            else:
                print("✅ Cookies有效：可正常访问全文")
                return True

        except Exception as e:
            print(f"❌ 验证会话时出错: {e}")
            return False

    def get_export_instructions(self) -> str:
        """
        返回cookies导出指引

        Returns:
            导出指引文本
        """
        return f"""
        🚀 Cookies 导出指引：

        1. 在Edge浏览器中安装 'Cookie Editor' 插件
        2. 访问 https://www.oilchem.net 并确保已登录
        3. 点击插件图标 → Export → JSON (默认格式)
        4. 保存为 '{self.cookies_file}' 文件
        5. 将文件放在代码同一目录下

        当前cookies文件: {self.cookies_file}
        """
