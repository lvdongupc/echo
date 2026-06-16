"""一次性脚本：生成 intent_cases.json 与 dialog_cases.json。"""
import json
from pathlib import Path

intent_cases: list = []


def add(label: str, messages: list[str]) -> None:
    for m in messages:
        intent_cases.append({"message": m, "expected_intent": label})


add("query", [
    "我的订单什么时候到？", "订单 #8821 物流到哪了", "查一下配送进度", "包裹显示已发货三天了还没到",
    "能告诉我预计送达时间吗", "快递单号 SF1234567890 现在在哪", "我的包裹卡在转运中心了",
    "订单状态一直是 processing 正常吗", "什么时候能收到商品", "配送超时了怎么办",
    "查订单 556677 的物流", "货运信息怎么查", "我的预售商品什么时候发货",
])
add("request", [
    "帮我取消订单", "请把订单改成明天配送", "我需要修改收货地址", "帮我申请退货",
    "请暂停我的订阅", "能不能换一个大一号的", "帮我备注放门口", "请重新发送验证码",
    "我需要开具电子发票", "帮我合并两个订单发货",
])
add("complaint", [
    "你们服务太差了！", "等了一个小时没人回复", "客服态度非常恶劣", "配送员把包裹扔在门口就跑了",
    "承诺48小时解决现在一周了", "产品质量和描述完全不符", "这次体验 horrible", "反复踢皮球没人负责",
])
add("technical", [
    "应用一直报500错误", "登录页面白屏", "App 闪退无法打开", "更新后无法启动",
    "一直提示 network error", "401 unauthorized 登录失败", "系统 crash 了三次",
    "接口 timeout 怎么办", "后台一直 loading", "OAuth 配置报错", "502 bad gateway",
    "数据库连接失败提示",
])
add("billing", [
    "为什么扣了两次款？", "退款多久到账", "发票开错了能重开吗", "订阅多扣了一个月",
    "支付失败但钱被扣了", "账单金额不对", "申请 refund 流程是什么", "自动续费怎么关",
    "扣款记录在哪里看", "这单能全额退款吗",
])
add("escalation", [
    "我要投诉，转人工！", "叫你们经理来", "必须转 supervisor 处理", "我要找人工客服",
    "这个问题必须升级处理", "请立即转接专员", "我不接受机器人回复了", "投诉到底找谁",
])
add("greeting", [
    "你好", "您好", "嗨", "hello", "Hi there", "早上好", "晚上好", "在吗",
])
add("account", [
    "修改我的邮箱地址", "忘记密码怎么办", "账户被锁定了", "怎么绑定手机号",
    "更换登录密码", "注销账户流程", "账号显示异常登录", "修改收货人姓名",
])
add("feedback", [
    "你们客服响应很快，点赞", "这次问题解决得很满意", "产品很好用谢谢", "服务体验不错",
    "处理效率很高，感谢",
])
add("other", [
    "今天天气怎么样", "随便聊聊", "asdfghjkl", "？？？", "嗯嗯",
])

intent_cases.extend([
    {
        "message": "那退款呢",
        "expected_intent": "billing",
        "history": [
            {"role": "user", "content": "订单有问题"},
            {"role": "assistant", "content": "请提供订单号"},
        ],
    },
    {
        "message": "还是登录不了",
        "expected_intent": "technical",
        "history": [
            {"role": "user", "content": "401 错误"},
            {"role": "assistant", "content": "请清除缓存重试"},
        ],
    },
    {
        "message": "帮我查一下",
        "expected_intent": "query",
        "history": [
            {"role": "user", "content": "我上周买的耳机"},
            {"role": "assistant", "content": "好的，请提供订单号"},
        ],
    },
    {
        "message": "转人工吧",
        "expected_intent": "escalation",
        "history": [
            {"role": "user", "content": "退款一直不到账"},
            {"role": "assistant", "content": "一般3-5个工作日"},
        ],
    },
    {
        "message": "谢谢解决了",
        "expected_intent": "feedback",
        "history": [
            {"role": "user", "content": "密码重置不了"},
            {"role": "assistant", "content": "已帮您重置"},
        ],
    },
])

dialog_cases = [
    {"question": "我的订单 #12345 还没到，已经超时了"},
    {"question": "应用登录一直报错 401"},
    {"question": "为什么这个月多扣了 50 块钱？"},
    {"question": "帮我把收货地址改成北京市朝阳区"},
    {"question": "退款政策是什么，7天内可以退吗"},
    {"question": "会员积分怎么兑换"},
    {"question": "配送范围包括港澳台吗"},
    {"question": "发票抬头怎么修改"},
    {"question": "App 更新后闪退怎么办"},
    {"question": "订阅自动续费如何取消"},
    {"turns": ["你好，我想退款", "订单号是 #12345", "退款多久能到账？"]},
    {"turns": ["登录一直失败", "错误码 401", "我已经清缓存了还是不行"]},
    {"turns": ["查一下物流", "订单 998877", "显示签收了但我没收到"]},
    {"turns": ["你好", "我想改邮箱", "新邮箱是 test@example.com"]},
    {"turns": ["被重复扣款了", "两笔都是 99 元", "请帮我处理退款"]},
    {"turns": ["产品坏了", "购买不到一周", "能换货吗"]},
    {"turns": ["我要投诉", "客服等了40分钟", "请转人工处理"]},
    {"turns": ["密码忘了", "收不到重置邮件", "邮箱是对的"]},
    {"turns": ["发票开错了", "抬头应该是公司名", "能重开吗"]},
    {"turns": ["配送太慢", "说三天到已经五天了", "能催一下吗"]},
    {"turns": ["你好", "在吗", "帮我查订单状态"]},
    {"turns": ["技术问题", "页面500", "刷新也没用"]},
    {"turns": ["取消订阅", "为什么还扣费", "请立即停止"]},
]

root = Path(__file__).parent
(root / "intent_cases.json").write_text(
    json.dumps(intent_cases, ensure_ascii=False, indent=2), encoding="utf-8"
)
(root / "dialog_cases.json").write_text(
    json.dumps(dialog_cases, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"intent cases: {len(intent_cases)}")
print(f"dialog cases: {len(dialog_cases)}")
