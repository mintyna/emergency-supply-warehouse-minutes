import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List
from datetime import datetime
from ..config import settings


class EmailSender:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.admin_email = settings.EMERGENCY_ADMIN_EMAIL

    def send_meeting_minutes(self,
                              to_emails: List[str],
                              meeting_minutes: str,
                              summary: Dict[str, Any],
                              attachments: List[str] = None) -> Dict[str, Any]:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = f"【应急物资会议纪要】{datetime.now().strftime('%Y-%m-%d')} 布局优化会议"
            
            html_body = self._generate_html_body(summary, meeting_minutes)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            minutes_attachment = MIMEBase('application', 'octet-stream')
            minutes_attachment.set_payload(meeting_minutes.encode('utf-8'))
            encoders.encode_base64(minutes_attachment)
            minutes_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="会议纪要_{datetime.now().strftime("%Y%m%d")}.md"'
            )
            msg.attach(minutes_attachment)
            
            if attachments:
                for file_path in attachments:
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{file_path.split("/")[-1]}"'
                    )
                    msg.attach(part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.smtp_user, to_emails, text)
            
            return {
                "success": True,
                "message": "邮件发送成功",
                "recipients": to_emails,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"邮件发送失败: {str(e)}",
                "recipients": to_emails,
                "timestamp": datetime.now().isoformat()
            }

    def _generate_html_body(self, summary: Dict[str, Any], meeting_minutes: str) -> str:
        urgent_count = len(summary.get('replenishment_plan', {}).get('urgent_items', []))
        action_count = len(summary.get('action_items', []))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; color: white; border-radius: 8px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header .date {{ margin-top: 10px; font-size: 14px; opacity: 0.9; }}
                .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 8px; border-left: 4px solid #667eea; }}
                .section h2 {{ color: #667eea; margin-top: 0; font-size: 18px; }}
                .summary-box {{ background: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 4px solid #0097a7; }}
                .alert-box {{ background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; }}
                .danger-box {{ background: #f8d7da; padding: 15px; border-radius: 8px; border-left: 4px solid #dc3545; }}
                .success-box {{ background: #d4edda; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-card {{ flex: 1; background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-card .number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
                .stat-card .label {{ font-size: 14px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #667eea; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
                .priority-high {{ color: #dc3545; font-weight: bold; }}
                .priority-medium {{ color: #ffc107; font-weight: bold; }}
                .priority-low {{ color: #28a745; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding: 20px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 应急物资储备库布局优化会议纪要</h1>
                <div class="date">发送时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</div>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="number">{urgent_count}</div>
                    <div class="label">紧急补库项</div>
                </div>
                <div class="stat-card">
                    <div class="number">{action_count}</div>
                    <div class="label">待办任务</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(summary.get('layout_adjustment', {}).get('warehouse_zones', []))}</div>
                    <div class="label">调整区域</div>
                </div>
            </div>

            <div class="section">
                <h2>📋 会议概述</h2>
                <div class="summary-box">
                    {summary.get('meeting_summary', '无')}
                </div>
            </div>
        """
        
        if summary.get('replenishment_plan', {}).get('urgent_items'):
            html += """
            <div class="section">
                <h2>⚠️ 紧急补库清单</h2>
                <div class="danger-box">
                    <table>
                        <tr><th>物资名称</th><th>物资编码</th><th>数量</th><th>截止期限</th></tr>
            """
            for item in summary['replenishment_plan']['urgent_items']:
                html += f"<tr><td>{item.get('material_name', '')}</td><td>{item.get('code', '')}</td><td>{item.get('quantity', '')}</td><td class='priority-high'>{item.get('deadline', '')}</td></tr>"
            html += "</table></div></div>"
        
        html += """
            <div class="section">
                <h2>🏭 仓库布局调整</h2>
                <table>
                    <tr><th>区域名称</th><th>存储物资</th><th>调整说明</th></tr>
        """
        for zone in summary.get('layout_adjustment', {}).get('warehouse_zones', []):
            html += f"<tr><td>{zone.get('zone_name', '')}</td><td>{', '.join(zone.get('materials', []))}</td><td>{zone.get('adjustment', '')}</td></tr>"
        html += "</table></div>"
        
        html += """
            <div class="section">
                <h2>✅ 行动计划</h2>
                <table>
                    <tr><th>任务</th><th>负责方</th><th>截止时间</th><th>优先级</th></tr>
        """
        for action in summary.get('action_items', []):
            priority_class = f"priority-{action.get('priority', 'low')}"
            priority_text = "高" if action.get('priority') == 'high' else "中" if action.get('priority') == 'medium' else "低"
            html += f"<tr><td>{action.get('task', '')}</td><td>{action.get('responsible', '')}</td><td>{action.get('deadline', '')}</td><td class='{priority_class}'>{priority_text}</td></tr>"
        html += "</table></div>"
        
        if summary.get('risk_assessment', {}).get('identified_risks'):
            html += """
            <div class="section">
                <h2>⚠️ 风险评估</h2>
                <div class="alert-box">
                    <strong>识别风险：</strong>
                    <ul>
            """
            for risk in summary['risk_assessment']['identified_risks']:
                html += f"<li>{risk}</li>"
            html += """
                    </ul>
                    <strong>缓解措施：</strong>
                    <ul>
            """
            for measure in summary['risk_assessment']['mitigation_measures']:
                html += f"<li>{measure}</li>"
            html += "</ul></div></div>"
        
        html += """
            <div class="footer">
                <p>此邮件由应急物资管理系统自动发送，请及时处理相关事项。</p>
                <p>如需查看详细会议纪要，请查阅附件。</p>
            </div>
        </body>
        </html>
        """
        
        return html

    def send_to_emergency_admin(self,
                                 meeting_minutes: str,
                                 summary: Dict[str, Any],
                                 attachments: List[str] = None) -> Dict[str, Any]:
        return self.send_meeting_minutes(
            to_emails=[self.admin_email],
            meeting_minutes=meeting_minutes,
            summary=summary,
            attachments=attachments
        )
