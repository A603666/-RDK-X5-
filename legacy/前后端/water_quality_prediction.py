#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水质数据预测分析脚本
使用真实水质数据进行LSTM预测分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 机器学习库
try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    ML_AVAILABLE = True
    print("✓ 机器学习库加载成功")
except ImportError as e:
    ML_AVAILABLE = False
    print(f"⚠️ 机器学习库未安装: {e}")
    print("正在安装必要的库...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'scikit-learn', 'matplotlib', 'seaborn'])
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    ML_AVAILABLE = True

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class WaterQualityPredictor:
    """水质预测器"""
    
    def __init__(self, sequence_length=48):
        self.sequence_length = sequence_length  # 使用48条数据预测下48条
        self.scalers = {}
        self.models = {}
        self.history = {}
        
    def load_data(self, csv_file):
        """加载水质数据"""
        print(f"正在加载数据文件: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        
        # 显示断面信息
        if '断面名称' in df.columns:
            sections = df['断面名称'].unique()
            print(f"可用断面: {sections}")
            return df, sections
        else:
            print("未找到断面名称列")
            return df, []
    
    def select_section_data(self, df, section_name):
        """选择特定断面的数据"""
        if '断面名称' not in df.columns:
            print("数据中没有断面名称列，使用全部数据")
            return df
            
        section_data = df[df['断面名称'] == section_name].copy()
        print(f"断面 '{section_name}' 的数据量: {len(section_data)}")
        
        if len(section_data) < self.sequence_length * 2:
            print(f"⚠️ 数据量不足，需要至少 {self.sequence_length * 2} 条数据")
            return None
            
        return section_data
    
    def preprocess_data(self, df, target_columns=['水温', 'pH', '溶解氧']):
        """数据预处理"""
        print("开始数据预处理...")
        
        # 检查目标列是否存在
        available_columns = []
        for col in target_columns:
            if col in df.columns:
                available_columns.append(col)
            else:
                print(f"⚠️ 列 '{col}' 不存在于数据中")
        
        if not available_columns:
            print("❌ 没有找到可用的目标列")
            return None, None
            
        print(f"使用列: {available_columns}")
        
        # 处理时间列
        if '监测时间' in df.columns:
            df['监测时间'] = pd.to_datetime(df['监测时间'])
            df = df.sort_values('监测时间').reset_index(drop=True)
        
        # 提取数值数据并处理缺失值
        data = df[available_columns].copy()
        
        # 转换为数值类型，非数值转为NaN
        for col in available_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # 显示缺失值信息
        missing_info = data.isnull().sum()
        print("缺失值统计:")
        for col, missing in missing_info.items():
            if missing > 0:
                print(f"  {col}: {missing} ({missing/len(data)*100:.1f}%)")
        
        # 填充缺失值（使用前向填充和后向填充）
        data = data.fillna(method='ffill').fillna(method='bfill')
        
        # 如果仍有缺失值，使用均值填充
        data = data.fillna(data.mean())
        
        print(f"预处理后数据形状: {data.shape}")
        print("数据统计信息:")
        print(data.describe())
        
        return data, available_columns
    
    def create_sequences(self, data, target_col):
        """创建时间序列数据"""
        values = data[target_col].values

        X, y = [], []
        # 创建滑动窗口数据
        for i in range(self.sequence_length, len(values)):
            X.append(values[i-self.sequence_length:i])
            y.append(values[i])

        return np.array(X), np.array(y)

    def create_prediction_sequences(self, data, target_col):
        """创建用于预测48个时间步的序列数据"""
        values = data[target_col].values

        X, y = [], []
        # 使用48个历史数据预测下48个数据
        for i in range(self.sequence_length, len(values) - self.sequence_length + 1):
            X.append(values[i-self.sequence_length:i])
            y.append(values[i:i+self.sequence_length])

        return np.array(X), np.array(y)

    def build_model(self, model_type='rf'):
        """构建机器学习模型"""
        if model_type == 'rf':
            return RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            return LinearRegression()
    
    def train_and_predict(self, data, target_columns):
        """训练模型并进行预测"""
        results = {}

        for col in target_columns:
            print(f"\n{'='*50}")
            print(f"正在处理参数: {col}")
            print(f"{'='*50}")

            # 数据标准化
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(data[[col]])
            self.scalers[col] = scaler

            # 创建序列数据用于预测48个时间步
            X, y = self.create_prediction_sequences(pd.DataFrame(scaled_data, columns=[col]), col)

            if len(X) == 0:
                print(f"⚠️ {col}: 数据不足，无法创建序列")
                continue

            print(f"序列数据形状: X={X.shape}, y={y.shape}")

            # 划分训练集和测试集
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # 为了使用传统ML模型，我们需要将多输出问题转换为多个单输出问题
            # 这里我们简化为预测下一个时间步，然后递归预测48步
            X_simple, y_simple = self.create_sequences(pd.DataFrame(scaled_data, columns=[col]), col)

            if len(X_simple) == 0:
                continue

            split_idx_simple = int(len(X_simple) * 0.8)
            X_train_simple = X_simple[:split_idx_simple]
            X_test_simple = X_simple[split_idx_simple:]
            y_train_simple = y_simple[:split_idx_simple]
            y_test_simple = y_simple[split_idx_simple:]

            # 构建和训练模型
            model = self.build_model('rf')

            print("开始训练模型...")
            model.fit(X_train_simple, y_train_simple)

            self.models[col] = model

            # 递归预测48步
            y_pred_sequences = []
            for i in range(len(X_test)):
                # 使用前48个数据点预测后48个
                current_sequence = X_test[i].copy()
                predictions = []

                for step in range(self.sequence_length):
                    # 预测下一个值
                    next_pred = model.predict([current_sequence])[0]
                    predictions.append(next_pred)

                    # 更新序列（滑动窗口）
                    current_sequence = np.append(current_sequence[1:], next_pred)

                y_pred_sequences.append(predictions)

            y_pred_sequences = np.array(y_pred_sequences)

            # 反标准化
            y_test_orig = scaler.inverse_transform(y_test.reshape(-1, 1)).reshape(y_test.shape)
            y_pred_orig = scaler.inverse_transform(y_pred_sequences.reshape(-1, 1)).reshape(y_pred_sequences.shape)

            # 计算性能指标
            mse = mean_squared_error(y_test_orig.flatten(), y_pred_orig.flatten())
            mae = mean_absolute_error(y_test_orig.flatten(), y_pred_orig.flatten())
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test_orig.flatten(), y_pred_orig.flatten())

            # 计算MAPE
            mape = np.mean(np.abs((y_test_orig.flatten() - y_pred_orig.flatten()) / np.maximum(np.abs(y_test_orig.flatten()), 1e-8))) * 100

            results[col] = {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2': r2,
                'mape': mape,
                'y_test': y_test_orig,
                'y_pred': y_pred_orig,
                'model_type': 'Random Forest'
            }

            print(f"\n{col} 预测性能指标:")
            print(f"  MSE (均方误差): {mse:.4f}")
            print(f"  MAE (平均绝对误差): {mae:.4f}")
            print(f"  RMSE (均方根误差): {rmse:.4f}")
            print(f"  R² (决定系数): {r2:.4f}")
            print(f"  MAPE (平均绝对百分比误差): {mape:.2f}%")

        return results
    
    def plot_results(self, results, section_name):
        """绘制预测结果"""
        n_params = len(results)
        fig, axes = plt.subplots(n_params, 2, figsize=(15, 5*n_params))
        
        if n_params == 1:
            axes = axes.reshape(1, -1)
        
        for i, (param, result) in enumerate(results.items()):
            # 预测结果对比
            ax1 = axes[i, 0]
            
            # 只显示前5个预测序列的对比
            n_show = min(5, len(result['y_test']))
            for j in range(n_show):
                ax1.plot(result['y_test'][j], label=f'真实值 {j+1}', alpha=0.7)
                ax1.plot(result['y_pred'][j], label=f'预测值 {j+1}', linestyle='--', alpha=0.7)
            
            ax1.set_title(f'{section_name} - {param} 预测对比')
            ax1.set_xlabel('时间步')
            ax1.set_ylabel(param)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 误差分布
            ax2 = axes[i, 1]
            errors = (result['y_test'] - result['y_pred']).flatten()
            ax2.hist(errors, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.set_title(f'{param} 预测误差分布')
            ax2.set_xlabel('预测误差')
            ax2.set_ylabel('频次')
            ax2.axvline(0, color='red', linestyle='--', alpha=0.7, label='零误差线')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{section_name}_prediction_results.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # 性能指标汇总图
        self.plot_performance_summary(results, section_name)
    
    def plot_performance_summary(self, results, section_name):
        """绘制性能指标汇总"""
        metrics = ['MSE', 'MAE', 'RMSE', 'R²', 'MAPE(%)']
        params = list(results.keys())
        
        fig, axes = plt.subplots(1, len(metrics), figsize=(20, 4))
        
        for i, metric in enumerate(metrics):
            values = []
            for param in params:
                if metric == 'MAPE(%)':
                    values.append(results[param]['mape'])
                else:
                    values.append(results[param][metric.lower().replace('²', '2')])
            
            axes[i].bar(params, values, color=plt.cm.Set3(np.linspace(0, 1, len(params))))
            axes[i].set_title(f'{metric}')
            axes[i].set_ylabel(metric)
            
            # 在柱子上显示数值
            for j, v in enumerate(values):
                axes[i].text(j, v, f'{v:.3f}', ha='center', va='bottom')
        
        plt.suptitle(f'{section_name} - 预测性能指标汇总', fontsize=16)
        plt.tight_layout()
        plt.savefig(f'{section_name}_performance_summary.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """主函数"""
    print("🌊 水质数据预测分析系统")
    print("=" * 50)
    
    # 初始化预测器
    predictor = WaterQualityPredictor(sequence_length=48)
    
    # 加载数据
    df, sections = predictor.load_data('水质数据.csv')
    
    if len(sections) == 0:
        print("❌ 未找到断面信息，程序退出")
        return
    
    # 选择数据量最多的断面
    section_counts = df['断面名称'].value_counts()
    print("\n断面数据量统计:")
    for section, count in section_counts.head(10).items():
        print(f"  {section}: {count} 条")
    
    # 选择数据量最多的断面
    selected_section = section_counts.index[0]
    print(f"\n选择断面: {selected_section} (数据量: {section_counts[selected_section]})")
    
    # 提取断面数据
    section_data = predictor.select_section_data(df, selected_section)
    if section_data is None:
        print("❌ 断面数据不足，程序退出")
        return
    
    # 数据预处理
    processed_data, target_columns = predictor.preprocess_data(section_data)
    if processed_data is None:
        print("❌ 数据预处理失败，程序退出")
        return
    
    # 训练和预测
    print(f"\n开始训练模型，使用 {predictor.sequence_length} 条数据预测下 {predictor.sequence_length} 条数据")
    results = predictor.train_and_predict(processed_data, target_columns)
    
    if not results:
        print("❌ 没有成功训练任何模型")
        return
    
    # 显示结果汇总
    print(f"\n{'='*60}")
    print(f"预测结果汇总 - 断面: {selected_section}")
    print(f"{'='*60}")
    
    for param, result in results.items():
        print(f"\n📊 {param} 预测性能:")
        print(f"  ✓ MSE: {result['mse']:.4f}")
        print(f"  ✓ MAE: {result['mae']:.4f}")
        print(f"  ✓ RMSE: {result['rmse']:.4f}")
        print(f"  ✓ R²: {result['r2']:.4f}")
        print(f"  ✓ MAPE: {result['mape']:.2f}%")
        
        # 性能评价
        if result['r2'] > 0.8:
            print(f"  🎉 {param} 预测效果优秀!")
        elif result['r2'] > 0.6:
            print(f"  👍 {param} 预测效果良好!")
        elif result['r2'] > 0.4:
            print(f"  ⚠️ {param} 预测效果一般")
        else:
            print(f"  ❌ {param} 预测效果较差")
    
    # 绘制结果
    predictor.plot_results(results, selected_section)
    
    print(f"\n✅ 分析完成！结果图表已保存为:")
    print(f"  📈 {selected_section}_prediction_results.png")
    print(f"  📊 {selected_section}_performance_summary.png")

if __name__ == "__main__":
    main()
