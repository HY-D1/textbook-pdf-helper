# Kimi (Moonshot AI) 成本指南

## 概述

Kimi (月之暗面) 是中国领先的 AI 公司，提供比 OpenAI 更便宜的 API 服务。

**官网**: https://platform.moonshot.cn/

## 价格对比

### 💰 每概念成本对比 (人民币)

| 提供商 | 模型 | 输入 | 输出 | 总计 |
|--------|------|------|------|------|
| **Kimi** | moonshot-v1-8k | ¥0.048 | ¥0.018 | **¥0.066** |
| **Kimi** | moonshot-v1-32k | ¥0.096 | ¥0.036 | **¥0.132** |
| OpenAI | gpt-4o-mini | ¥0.44 | ¥0.66 | ¥1.10 |
| OpenAI | gpt-4o | ¥11.00 | ¥16.50 | ¥27.50 |

**Kimi 比 OpenAI GPT-4o-mini 便宜约 17 倍！**

### 📊 实际例子：30 个概念的教材

| 提供商 | 模型 | 总成本 (RMB) |
|--------|------|-------------|
| ⭐ Kimi | moonshot-v1-8k | **¥1.98** |
| Kimi | moonshot-v1-32k | ¥3.96 |
| OpenAI | gpt-4o-mini | ¥33.00 |
| OpenAI | gpt-4o | ¥825.00 |

## 使用方法

### 1. 获取 API Key

1. 访问 https://platform.moonshot.cn/
2. 注册账号
3. 创建 API Key
4. 充值 (支持支付宝、微信)

### 2. 设置环境变量

```bash
# 设置 Kimi API Key
export KIMI_API_KEY='sk-your-key-here'

# 或者使用 MOONSHOT_API_KEY
export MOONSHOT_API_KEY='sk-your-key-here'
```

添加到 `~/.bashrc` 或 `~/.zshrc` 使其永久生效：

```bash
echo 'export KIMI_API_KEY="sk-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. 使用 Kimi 生成教育笔记

#### 命令行方式

```bash
# 使用 Kimi 生成 (推荐)
algl-pdf edu generate textbook.pdf --llm-provider kimi

# 先估算成本
algl-pdf edu generate textbook.pdf --llm-provider kimi --estimate-cost

# 查看成本对比
algl-pdf edu cost
```

#### Python API 方式

```python
from algl_pdf_helper.educational_pipeline import EducationalNoteGenerator

# 使用 Kimi
generator = EducationalNoteGenerator(
    llm_provider="kimi",  # 或 LLMProvider.KIMI
)

# 估算成本
cost = generator.estimate_cost(num_concepts=30)
print(f"预计成本: ¥{cost['cost_rmb']['total']} RMB")

# 生成笔记
result = generator.process_pdf(
    pdf_path="textbook.pdf",
    output_dir="./output",
)
```

## 成本计算

### 每概念成本公式

```
输入: 4,000 tokens × ¥0.012 / 1K = ¥0.048
输出: 1,500 tokens × ¥0.012 / 1K = ¥0.018
总计: ¥0.066 RMB/概念
```

### 完整教材估算

| 教材类型 | 概念数量 | Kimi 8K 成本 | OpenAI mini 成本 |
|---------|---------|-------------|-----------------|
| 简单教程 | 10 个 | ¥0.66 | ¥11.00 |
| 标准教材 | 30 个 | ¥1.98 | ¥33.00 |
| 综合教材 | 50 个 | ¥3.30 | ¥55.00 |
| 百科全书 | 100 个 | ¥6.60 | ¥110.00 |

## 模型选择建议

### moonshot-v1-8k (推荐)
- **适用**: 大多数教材章节
- **上下文**: 8K tokens
- **价格**: ¥0.012/1K tokens
- **性价比**: 最高

### moonshot-v1-32k
- **适用**: 长章节、复杂概念
- **上下文**: 32K tokens
- **价格**: ¥0.024/1K tokens
- **用途**: 需要更多上下文的场景

### moonshot-v1-128k
- **适用**: 整章处理、大型文档
- **上下文**: 128K tokens
- **价格**: ¥0.12/1K tokens
- **用途**: 一次性处理大量内容

## 充值与计费

### 充值方式
- 支付宝
- 微信支付
- 银行转账

### 计费规则
- 按 token 计费
- 输入和输出分别计费
- 实时扣费
- 余额不足时会失败

### 查看用量
登录 https://platform.moonshot.cn/ 查看：
- 实时余额
- 用量统计
- 消费记录
- API 调用日志

## 成本优化技巧

### 1. 预处理减少 Tokens
```python
# 提取核心内容，去除无关文字
text = extract_core_content(raw_text)  # 减少输入 tokens
```

### 2. 批量处理
- 一次性处理多个概念
- 减少 API 调用次数
- 降低固定开销

### 3. 使用 8K 模型
- 8K 模型最便宜
- 适合大多数教材
- 32K/128K 仅在需要时使用

### 4. 缓存结果
- 保存已生成的笔记
- 避免重复生成
- 节省成本

## 完整示例

### 场景：处理 MySQL 教材

```bash
# 1. 设置 API Key
export KIMI_API_KEY='sk-your-key-here'

# 2. 查看成本对比
algl-pdf edu cost

# 3. 估算成本 (30 个概念)
algl-pdf edu generate murachs-mysql.pdf \
    --llm-provider kimi \
    --estimate-cost

# 输出：
# Provider: kimi
# Model: moonshot-v1-8k
# Concepts: 30
# Estimated Cost (RMB): ¥1.98

# 4. 生成教育笔记
algl-pdf edu generate murachs-mysql.pdf \
    --llm-provider kimi \
    --output-dir ./mysql-notes

# 5. 导出到 SQL-Adapt
algl-pdf export-edu murachs-mysql.pdf \
    --llm-provider kimi \
    --output-dir /path/to/sql-adapt
```

## 常见问题

### Q: Kimi 生成质量如何？
A: Kimi 基于 Moonshot 的大模型，中文理解能力强，生成质量优秀，特别适合中文教材。

### Q: 为什么比 OpenAI 便宜这么多？
A: 中国本土公司，运营成本低，且有价格优势策略。

### Q: 需要翻墙吗？
A: 不需要，国内直接访问，速度快。

### Q: 支持开发票吗？
A: 支持，可在平台申请企业发票。

### Q: 有免费额度吗？
A: 新用户注册有少量免费额度，可用于测试。

## 总结

| 维度 | Kimi | OpenAI |
|------|------|--------|
| 成本 | ⭐⭐⭐⭐⭐ 超便宜 | ⭐⭐⭐ 较贵 |
| 速度 | ⭐⭐⭐⭐⭐ 国内快 | ⭐⭐⭐ 需翻墙 |
| 中文 | ⭐⭐⭐⭐⭐ 原生强 | ⭐⭐⭐⭐ 良好 |
| 稳定性 | ⭐⭐⭐⭐⭐ 国内稳 | ⭐⭐⭐⭐ 偶尔不稳 |
| 易用性 | ⭐⭐⭐⭐⭐ API 兼容 | ⭐⭐⭐⭐ 标准 |

**推荐：使用 Kimi (moonshot-v1-8k) 处理教材，成本最低且效果优秀！**
