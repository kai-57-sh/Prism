import React from 'react';
import { Clock, MoreHorizontal, Play, Plus } from 'lucide-react';
import { motion } from 'framer-motion';

export const LandingView = () => {
  return (
    <div className="p-8 h-full overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-900 mb-2">欢迎回来，创作者</h1>
        <p className="text-zinc-500">选择一个模板开始，或继续之前的项目。</p>
      </header>

      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-800">推荐模板</h2>
          <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">查看全部</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
           <TemplateCard 
              title="健康科普：糖尿病饮食" 
              duration="60s" 
              type="扁平插画" 
              color="bg-orange-100" 
              icon="🥗"
           />
           <TemplateCard 
              title="日常急救小知识" 
              duration="45s" 
              type="真人实拍" 
              color="bg-blue-100" 
              icon="🚑"
           />
           <TemplateCard 
              title="儿童疫苗接种指南" 
              duration="90s" 
              type="MG 动画" 
              color="bg-green-100" 
              icon="💉"
           />
           <div className="border-2 border-dashed border-zinc-200 rounded-2xl flex flex-col items-center justify-center h-48 cursor-pointer hover:border-primary-300 hover:bg-primary-50 transition-all group">
              <div className="w-12 h-12 bg-zinc-100 rounded-full flex items-center justify-center mb-3 group-hover:bg-white group-hover:shadow-sm text-zinc-400 group-hover:text-primary-600 transition-all">
                <Plus size={24} />
              </div>
              <span className="text-zinc-500 font-medium group-hover:text-primary-700">新建空白项目</span>
           </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-800">最近项目</h2>
        </div>
        <div className="space-y-3">
          <ProjectRow 
            title="高血压预防指南" 
            date="2小时前" 
            status="草稿" 
            thumbnail="bg-indigo-100"
          />
          <ProjectRow 
            title="夏季防晒误区" 
            date="昨天" 
            status="生成中" 
            thumbnail="bg-yellow-100"
          />
          <ProjectRow 
            title="正确洗手七步法" 
            date="3天前" 
            status="已完成" 
            thumbnail="bg-teal-100"
          />
        </div>
      </div>
    </div>
  );
};

const TemplateCard = ({ title, duration, type, color, icon }: any) => (
  <motion.div 
    whileHover={{ y: -4 }}
    className="bg-white rounded-2xl p-4 border border-zinc-100 shadow-sm hover:shadow-md transition-all cursor-pointer group"
  >
    <div className={`h-32 rounded-xl ${color} mb-4 flex items-center justify-center text-4xl shadow-inner`}>
      {icon}
    </div>
    <h3 className="font-semibold text-zinc-800 mb-1 group-hover:text-primary-700 transition-colors">{title}</h3>
    <div className="flex items-center gap-3 text-xs text-zinc-500">
      <span className="bg-zinc-100 px-2 py-0.5 rounded text-zinc-600">{type}</span>
      <span className="flex items-center gap-1"><Clock size={12} /> {duration}</span>
    </div>
  </motion.div>
);

const ProjectRow = ({ title, date, status, thumbnail }: any) => (
  <div className="flex items-center p-3 bg-white rounded-xl border border-zinc-100 hover:border-primary-100 hover:shadow-sm transition-all cursor-pointer group">
    <div className={`w-16 h-10 rounded-lg ${thumbnail} mr-4 flex-shrink-0`}></div>
    <div className="flex-1">
      <h4 className="font-medium text-zinc-800 group-hover:text-primary-700">{title}</h4>
      <p className="text-xs text-zinc-500">{date}</p>
    </div>
    <div className="flex items-center gap-4">
      <span className={`text-xs px-2 py-1 rounded-full ${
        status === '已完成' ? 'bg-green-100 text-green-700' : 
        status === '生成中' ? 'bg-blue-100 text-blue-700' : 'bg-zinc-100 text-zinc-600'
      }`}>
        {status}
      </span>
      <button className="p-2 hover:bg-zinc-100 rounded-full text-zinc-400 hover:text-zinc-600">
        <MoreHorizontal size={16} />
      </button>
    </div>
  </div>
);
