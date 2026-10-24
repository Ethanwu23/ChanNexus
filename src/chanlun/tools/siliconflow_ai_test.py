import json
import os
import requests


MODEL_NAME = "deepseek-ai/DeepSeek-V4-Pro"  # 举例，换成你实际用的

def call_siliconflow_ai(
    prompt: str,
    api_token: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    # 精简参数：仅保留硅基流动必选/通用参数
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": temperature,
        "top_p": 0.7,
        "max_tokens": max_tokens,
    }
    try:
        # 延长超时时间至120秒
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"ok": False, "msg": f"HTTP 请求失败：{e}", "model": model}
    except json.JSONDecodeError:
        return {"ok": False, "msg": "返回结果不是合法 JSON", "model": model}
    if "choices" not in data or not data["choices"]:
        return {
            "ok": False,
            "msg": data.get("error", {}).get("message", "未知错误"),
            "model": model,
        }
    return {"ok": True, "msg": data["choices"][0]["message"]["content"], "model": model}

def build_chan_prompt(
    code: str,
    name: str,
    frequency: str,
    current_time: str,
    price: float,
    bis: list[dict],
    xds: list[dict],
    zss: list[dict],
) -> str:
    """
    构建缠论分析提示词
    """
    prompt = "```markdown\n"
    prompt += "# 缠论技术分析\n\n"
    prompt += "请根据以下缠论数据，分析后续可能走势，并按概率排序输出。\n"
    prompt += "**输出格式必须是 Markdown**\n\n"

    prompt += f"## 当前品种\n"
    prompt += f"- **代码/名称**：`{code} - {name}`\n"
    prompt += f"- **周期**：`{frequency}`\n"
    prompt += f"- **时间**：`{current_time}`\n"
    prompt += f"- **最新价**：`{price}`\n\n"

    # 笔
    prompt += "## 最新笔数据\n\n"
    prompt += "| 起始时间 | 结束时间 | 方向 | 区间 | 完成 | 买点 | 背驰 |\n"
    prompt += "|---------|---------|------|------|------|------|------|\n"
    for bi in bis[-9:]:
        prompt += (
            f"| {bi['start_time']} | {bi['end_time']} "
            f"| {bi['direction']} | {bi['start_val']} - {bi['end_val']} "
            f"| {bi['done']} | {bi['mmd']} | {bi['bc']} |\n"
        )

    # 线段
    prompt += "\n## 最新线段数据\n\n"
    prompt += "| 起始时间 | 结束时间 | 方向 | 区间 | 完成 | 买点 | 背驰 |\n"
    prompt += "|---------|---------|------|------|------|------|------|\n"
    for xd in xds[-3:]:
        prompt += (
            f"| {xd['start_time']} | {xd['end_time']} "
            f"| {xd['direction']} | {xd['start_val']} - {xd['end_val']} "
            f"| {xd['done']} | {xd['mmd']} | {xd['bc']} |\n"
        )

    # 中枢
    prompt += "\n## 中枢信息\n\n"
    prompt += "| 起始时间 | 结束时间 | 类型 | 最高 | 最低 | 中枢上沿 | 中枢下沿 |\n"
    prompt += "|---------|---------|------|------|------|----------|----------|\n"
    for zs in zss[-2:]:
        prompt += (
            f"| {zs['start_time']} | {zs['end_time']} "
            f"| {zs['type']} | {zs['gg']} | {zs['dd']} "
            f"| {zs['zg']} | {zs['zd']} |\n"
        )

    prompt += "\n---\n"
    prompt += "请结合笔、线段、中枢，给出后续走势推演及操作建议。\n"
    prompt += "```"
    return prompt

if __name__ == "__main__":
    prompt = build_chan_prompt(
        code="SH.000001",
        name="上证指数",
        frequency="日线",
        current_time="2026-06-04 15:00",
        price=3245.67,
        bis=[
            {
                "start_time": "2026-05-20",
                "end_time": "2026-05-28",
                "direction": "向上",
                "start_val": 3140,
                "end_val": 3274,
                "done": "是",
                "mmd": "三买",
                "bc": "盘整背驰",
            }
        ],
        xds=[
            {
                "start_time": "2026-03-01",
                "end_time": "2026-06-01",
                "direction": "向下",
                "start_val": 3674,
                "end_val": 3140,
                "done": "否",
                "mmd": "",
                "bc": "",
            }
        ],
        zss=[
            {
                "start_time": "2026-04-10",
                "end_time": "2026-06-01",
                "type": "震荡中枢",
                "gg": 3509,
                "dd": 3140,
                "zg": 3400,
                "zd": 3227,
            }
        ],
    )

    print(prompt)
    result = call_siliconflow_ai(
        prompt=prompt,
        api_token=os.environ["CHANNEXUS_SILICONFLOW_API_TOKEN"],
        model=MODEL_NAME,
    )

    if result["ok"]:
        print("分析成功：\n")
        print(result["msg"])
    else:
        print("分析失败：", result["msg"])
