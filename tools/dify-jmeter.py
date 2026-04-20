from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from pathlib import Path

import os
import base64
import tempfile
import subprocess

class DifyJmeterTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 获取base64编码的jmx原文, 并解析为jmx文件
        jmx_raw = tool_parameters["jmx_b64"]
        def fix_base64_padding(s):
            return s + "=" * (4 - len(s) % 4)
        jmx_raw = fix_base64_padding(jmx_raw)
        jmx_ctx = base64.b64decode(jmx_raw)
       
        # 写入script.jmx文件
        temp_dir = tempfile.gettempdir()
        jmx_file = Path(temp_dir) / "script.jmx"
        jtl_file = Path(temp_dir) / "result.jtl"
        report_dir = Path(temp_dir) / "jmeter-report"
        jmx_file.write_bytes(jmx_ctx)

        # 环境配置
        current_file = Path(__file__).resolve()
        jre_dir = current_file.parent.parent / "_assets" / "jre"
        jre_bin = jre_dir / "bin" / "java.exe"
        jmeter_dir = current_file.parent.parent / "_assets" / "jmeter"
        jmeter_bin = jmeter_dir / "bin" / "jmeter.bat"
        
        env = os.environ.copy()
        env["JRE_HOME"] = str(jre_dir)
        env["JAVA_HOME"] = str(jre_dir)
        
        jre_bin.chmod(0o755)
        jmeter_bin.chmod(0o755)

        # 执行jmeter
        cmd = [
            str(jmeter_bin), "-n",
            "-t", str(jmx_file),
            "-l", str(jtl_file),
            "-e", "-o", str(report_dir)
        ]

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        print("\n" + "="*50)
        print("JMETER 执行完成，控制台输出如下：")
        print("="*50)
        print("[标准输出]")
        print(result.stdout)

        print("\n[错误输出]")
        print(result.stderr)
        print(f"返回码: {result.returncode}")
        print("="*50 + "\n")

        yield self.create_json_message({
            "status": "success" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "jmx": str(jmx_file),
            "jtl": str(jtl_file),
            "report": str(report_dir),
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-3000:]
        })