# EchoMind 评测报告

**生成时间:** 2026-06-16T15:11:29.708682  
**通过率:** 50/50 (100.0%)

## 数据集规模

| 类型 | 数量 |
|------|------|
| 意图识别用例 | 92 |
| 对话用例（组） | 23 |
| 对话总轮次 | 49 |

### 意图分布

- `account`: 8
- `billing`: 11
- `complaint`: 8
- `escalation`: 9
- `feedback`: 6
- `greeting`: 8
- `other`: 5
- `query`: 14
- `request`: 10
- `technical`: 13

## 平均得分

| 指标 | 分数 |
|------|------|
| accuracy | 0.9959 |
| completeness | 0.8429 |
| helpfulness | 0.9214 |
| intent_accuracy | 0.8913 |
| relevance | 0.9898 |

## 意图识别（按类别）

| 意图 | Precision | Recall | F1 |
|------|-----------|--------|-----|
| account | 1.000 | 0.750 | 0.857 |
| billing | 1.000 | 0.545 | 0.706 |
| complaint | 0.800 | 1.000 | 0.889 |
| escalation | 1.000 | 0.889 | 0.941 |
| feedback | 1.000 | 1.000 | 1.000 |
| greeting | 1.000 | 1.000 | 1.000 |
| other | 1.000 | 1.000 | 1.000 |
| query | 0.857 | 0.857 | 0.857 |
| request | 0.625 | 1.000 | 0.769 |
| technical | 1.000 | 1.000 | 1.000 |

**Accuracy:** 89.1%  
**Macro-F1:** 0.902  

## 对话质量（LLM-as-Judge）

| 用例 | 综合分 | 通过 |
|------|--------|------|
| dialog_0 | 0.825 | ✓ |
| dialog_1 | 1.000 | ✓ |
| dialog_2 | 0.963 | ✓ |
| dialog_3 | 1.000 | ✓ |
| dialog_4 | 1.000 | ✓ |
| dialog_5 | 0.925 | ✓ |
| dialog_6 | 1.000 | ✓ |
| dialog_7 | 0.900 | ✓ |
| dialog_8 | 0.750 | ✓ |
| dialog_9 | 0.875 | ✓ |
| dialog_10_turn_0 | 0.850 | ✓ |
| dialog_10_turn_1 | 0.850 | ✓ |
| dialog_10_turn_2 | 0.963 | ✓ |
| dialog_11_turn_0 | 0.900 | ✓ |
| dialog_11_turn_1 | 0.988 | ✓ |
| dialog_11_turn_2 | 0.988 | ✓ |
| dialog_12_turn_0 | 0.887 | ✓ |
| dialog_12_turn_1 | 0.887 | ✓ |
| dialog_12_turn_2 | 0.975 | ✓ |
| dialog_13_turn_0 | 1.000 | ✓ |
| dialog_13_turn_1 | 0.963 | ✓ |
| dialog_13_turn_2 | 1.000 | ✓ |
| dialog_14_turn_0 | 0.988 | ✓ |
| dialog_14_turn_1 | 0.988 | ✓ |
| dialog_14_turn_2 | 0.950 | ✓ |
| dialog_15_turn_0 | 0.825 | ✓ |
| dialog_15_turn_1 | 0.925 | ✓ |
| dialog_15_turn_2 | 0.963 | ✓ |
| dialog_16_turn_0 | 0.925 | ✓ |
| dialog_16_turn_1 | 0.975 | ✓ |
| dialog_16_turn_2 | 1.000 | ✓ |
| dialog_17_turn_0 | 0.850 | ✓ |
| dialog_17_turn_1 | 0.988 | ✓ |
| dialog_17_turn_2 | 0.988 | ✓ |
| dialog_18_turn_0 | 0.988 | ✓ |
| dialog_18_turn_1 | 0.988 | ✓ |
| dialog_18_turn_2 | 0.975 | ✓ |
| dialog_19_turn_0 | 0.875 | ✓ |
| dialog_19_turn_1 | 0.925 | ✓ |
| dialog_19_turn_2 | 0.975 | ✓ |
| dialog_20_turn_0 | 1.000 | ✓ |
| dialog_20_turn_1 | 0.950 | ✓ |
| dialog_20_turn_2 | 0.875 | ✓ |
| dialog_21_turn_0 | 0.825 | ✓ |
| dialog_21_turn_1 | 0.988 | ✓ |
| dialog_21_turn_2 | 0.988 | ✓ |
| dialog_22_turn_0 | 0.825 | ✓ |
| dialog_22_turn_1 | 0.950 | ✓ |
| dialog_22_turn_2 | 0.963 | ✓ |

## 意图识别错误样本

| 消息 | 期望 | 预测 | 置信度 |
|------|------|------|--------|
| 包裹显示已发货三天了还没到 | query | complaint | 0.85 |
| 配送超时了怎么办 | query | complaint | 0.85 |
| 发票开错了能重开吗 | billing | request | 0.95 |
| 申请 refund 流程是什么 | billing | query | 0.95 |
| 扣款记录在哪里看 | billing | query | 0.95 |
| 这单能全额退款吗 | billing | request | 0.95 |
| 我要找人工客服 | escalation | request | 0.95 |
| 怎么绑定手机号 | account | request | 0.95 |
| 注销账户流程 | account | request | 0.95 |
| 那退款呢 | billing | request | 0.85 |

## 优化建议

- 意图识别准确率 < 90%：增加 Few-shot 示例，或对低 F1 的意图类别补充训练数据
