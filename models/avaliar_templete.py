# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class AvaliarTemplate(models.Model):
    _name = "avaliar.template"
    _description = 'Avaliar Template'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Selection([
        ('essencial', 'Essencial'),
        ('gerencial', 'Gerencial')
    ], string="Tipo", required=True)    # avaliar_ids = fields.Many2many("avaliacaodesempenho.avaliacaodesempenho", 'avaliar_ids_rel', string="Avaliar")

class comissaoTemplate(models.Model):
    _name = "comissao.template"
    _description = 'Comissao Template'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char("Name", required=True)
    # comissao_id = fields.Many2many("comissao.avaliadora", string="Departamento")
    funcionario_id = fields.Many2one('hr.employee', string='Avaliador', ondelete='cascade', required=True, tracking=True)

class ComissaoType(models.Model):
    _name = 'comissao.tipo'
    _description = 'Tipo de Comissao'

    name = fields.Char(string='Name', required=True)
    departamento = fields.Many2one('hr.department', string='Departamento', required=True)
    cargo = fields.Char(string='Cargo', required=True)
    funcionario_id = fields.Many2one('hr.employee', string='Funcionario', ondelete='cascade', required=True)
    funcionario_avaliacao_id = fields.Many2one('avaliar.funcionario', string='Funcionario Avaliacao', ondelete='cascade')


class Avalia(models.Model):
    _name = "avaliar.funcionario"
    _description = "Avaliar Funcionario"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Many2one('hr.employee', string='Nome', ondelete='cascade', required=True, tracking=True)
    cargo = fields.Many2one(related='name.job_id', related_sudo=True, string='Cargo', store=True,tracking=True)
    departamento = fields.Many2one('hr.department', string='Departamento', store=True,tracking=True)
    avaliador = fields.Many2one('hr.employee', string='Avaliador', ondelete='cascade', required=True, default=lambda self: self.env.user.employee_id.id, tracking=True)
    cargo_avaliador = fields.Many2one(related='avaliador.job_id', related_sudo=True, string="Cargo", required=True, tracking=True)
    data_aprovacao = fields.Datetime(string="Data", required=True, default=fields.Datetime.now, tracking=True)
    anotacoes = fields.Text(string='Anotacoes', required=True,tracking=True)
    assinatura_colaborador = fields.Char(string="Ass. Colaborador",tracking=True)
    assinatura_avaliador = fields.Char(string="Ass. do Avaliador",tracking=True)
    assinatura_responsavel = fields.Char(string="Ass.do responsavel pelo RH",tracking=True)
    status = fields.Selection(
        [('novo', 'Novo'),
         ('espera', 'Em espera'),
         ('aprovar', 'Aprovado'),
         ('concluir', 'Concluido'),
         ('cancelar', 'Cancelado'),
         ('rejeitar', 'Rejeitado')],
        default="novo",
        string="Status", tracking=True)
    check_list = fields.Many2many('avaliar.template', 'avaliar_teste_rel', string="Tipo de competência", required =True, tracking=True)
    custom_checklist_ids = fields.One2many("avaliacao.tipo", 'funcionario_id', string="Competência", required=True, tracking=True)
    relatorio_id = fields.Many2one('relatorio.avaliacoes', string="Relatório", tracking=True)
    total_nota = fields.Float(string='Total Nota', compute='calcular_nota_total', store=True)
    comissao_list = fields.Many2one('comissao.avaliadora', string="Comissao Avaliadora", tracking=True)
    comissao_checklist_ids = fields.One2many("comissao.tipo", 'funcionario_avaliacao_id', string="Comissao",required=True, tracking=True)
    should_hide_total_nota = fields.Boolean(string='Should Hide Total Nota', compute='_compute_should_hide_total_nota', tracking=True)
    texto_nota = fields.Text(
        string="Classificação da Nota",
        default="Classificação da Nota:"
                "- Nota entre 0 e 3: Péssimo"
                "- Nota entre 3 e 6: Médio"
                "- Nota entre 6 e 10: Excelente",
        readonly=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
        tracking=True)
    planilha_id = fields.Many2one('planilha.avaliacao',string="Planilha de Avaliação",required=True, tracking=True)
    @api.model
    def default_get(self, fields_list):
        res = super(Avalia, self).default_get(fields_list)

        employee = self.env.user.employee_id

        if not employee:
            return res

        return res

    @api.onchange('avaliador', 'comissao_list')
    def _onchange_avaliador_domain(self):

        current_employee = self.env.user.employee_id
        if not current_employee:
            return {
                'domain': {
                    'comissao_list': [('id', '=', False)],
                    'name': [('id', '=', False)],
                    'avaliador': [('id', '=', False)]
                }
            }

        current_employee_id = current_employee.id

        # =========================
        # COMISSÕES ONDE ELE É AVALIADOR
        # =========================
        comissoes_avaliador = self.env['comissao.avaliadora'].search([
            ('avaliador_ids', 'in', current_employee_id)
        ])

        if comissoes_avaliador:

            funcionario_ids = comissoes_avaliador.with_context(
                active_test=False
            ).funcionario_ids.ids

            return {
                'domain': {

                    # mostra somente as comissões
                    'comissao_list': [
                        ('id', 'in', comissoes_avaliador.ids)
                    ],

                    # mostra somente funcionários
                    # dessas comissões
                    'name': [
                        ('id', 'in', funcionario_ids)
                    ],

                    # mostra apenas ele como avaliador
                    'avaliador': [
                        ('id', '=', current_employee_id)
                    ]
                }
            }

        # =========================
        # FUNCIONÁRIO NORMAL
        # =========================
        else:

            comissoes_funcionario = self.env['comissao.avaliadora'].search([
                ('funcionario_ids', 'in', current_employee_id)
            ])

            avaliador_ids = comissoes_funcionario.with_context(
                active_test=False
            ).avaliador_ids.ids

            return {
                'domain': {

                    'comissao_list': [
                        ('id', 'in', comissoes_funcionario.ids)
                    ],

                    'name': [
                        ('id', '=', current_employee_id)
                    ],

                    'avaliador': [
                        ('id', 'in', avaliador_ids)
                    ]
                }
            }
    @api.depends('avaliador')
    def _compute_comissao(self):
        user = self.env.user
        domain = {'comissao_list': []}
        comissoes = self.env['comissao.avaliadora'].search([('comissao_id.avaliador_ids', 'in', [user.id])])
        domain = {'comissao_list': [('id', 'in', comissoes.ids)]}

        return {'domain': domain}

    @api.depends('custom_checklist_ids.nota')
    def _compute_should_hide_total_nota(self):
        for record in self:
            hide = any(not checklist.nota for checklist in record.custom_checklist_ids)
            record.should_hide_total_nota = hide

    @api.constrains('custom_checklist_ids')
    def _check_checklist_not_empty(self):
        for record in self:
            if any(not checklist.nota for checklist in record.custom_checklist_ids):
                raise UserError("Por favor, adicione as notas na avaliação antes de salvar.")

    @api.model
    def create(self, vals):
        """Valida notas e impede avaliação duplicada no mesmo mês."""
        if any(
                not checklist.get('nota')
                for checklist in vals.get('custom_checklist_ids', [])
                if isinstance(checklist, dict)
        ):
            raise UserError(_("Por favor, adicione todas as notas na avaliação antes de salvar."))

        funcionario_id = vals.get('name')
        data_aprovacao = vals.get('data_aprovacao', fields.Datetime.now())
        data = fields.Datetime.from_string(data_aprovacao)

        if funcionario_id:
            inicio_mes = data.replace(day=1, hour=0, minute=0, second=0)
            if data.month == 12:
                proximo_mes = data.replace(year=data.year + 1, month=1, day=1)
            else:
                proximo_mes = data.replace(month=data.month + 1, day=1)

            existente = self.env['avaliar.funcionario'].search([
                ('name', '=', funcionario_id),
                ('data_aprovacao', '>=', inicio_mes),
                ('data_aprovacao', '<', proximo_mes),
            ], limit=1)

            if existente:
                funcionario_nome = self.env['hr.employee'].sudo().browse(funcionario_id).name
                raise ValidationError(_(
                    f"O colaborador {funcionario_nome} já foi avaliado este mês ({data.strftime('%B/%Y')}). "
                    "Só poderá ser avaliado novamente no próximo mês."
                ))

        res = super(Avalia, self).create(vals)
        return res

    def write(self, vals):
        """Valida notas e impede avaliação duplicada no mesmo mês durante edição."""
        if 'custom_checklist_ids' in vals:
            for checklist in vals.get('custom_checklist_ids', []):
                if isinstance(checklist, dict) and not checklist.get('nota'):
                    raise UserError(_("Por favor, adicione todas as notas na avaliação antes de salvar."))
        for record in self:
            funcionario_id = vals.get('name', record.name.id)
            data_aprovacao = vals.get('data_aprovacao', record.data_aprovacao)
            data = fields.Datetime.from_string(data_aprovacao)

            inicio_mes = data.replace(day=1, hour=0, minute=0, second=0)
            if data.month == 12:
                proximo_mes = data.replace(year=data.year + 1, month=1, day=1)
            else:
                proximo_mes = data.replace(month=data.month + 1, day=1)
            existente = self.env['avaliar.funcionario'].search([
                ('name', '=', funcionario_id),
                ('data_aprovacao', '>=', inicio_mes),
                ('data_aprovacao', '<', proximo_mes),
                ('id', '!=', record.id),
            ], limit=1)
            if existente:
                funcionario_nome = self.env['hr.employee'].sudo().browse(funcionario_id).name
                raise ValidationError(_(
                    f"O colaborador {funcionario_nome} já foi avaliado este mês ({data.strftime('%B/%Y')}). "
                    "Só poderá ser avaliado novamente no próximo mês."
                ))
        res = super(Avalia, self).write(vals)
        return res

    @api.depends('custom_checklist_ids.peso', 'custom_checklist_ids.nota')
    def calcular_nota_total(self):

        for record in self:

            total_obtido = 0.0
            total_peso = 0.0

            for item in record.custom_checklist_ids:

                nota = item.nota or 0
                peso = item.peso or 0

                # ==================================
                # COMPETÊNCIA GERENCIAL
                # peso dobrado
                # ==================================
                if item.competencia == 'gerencial':

                    total_obtido += nota * 2
                    total_peso += peso * 2

                # ==================================
                # COMPETÊNCIA ESSENCIAL
                # ==================================
                else:

                    total_obtido += nota
                    total_peso += peso

            if total_peso > 0:
                record.total_nota = (total_obtido / total_peso) * 100
            else:
                record.total_nota = 0

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.departamento = self.name.sudo().department_id.id
            comissao_templates = self.env['comissao.avaliadora'].search([
                ('avaliador_ids', 'in', self.avaliador.id)
            ])
            if comissao_templates:
                return {'domain': {'comissao_list': [('id', 'in', comissao_templates.ids)]}}
            else:
                return {'domain': {'comissao_list': []}}
        else:
            return {'domain': {'comissao_list': []}}

    @api.onchange('comissao_list')
    def _onchange_comissao_list(self):

        self.planilha_id = False
        self.custom_checklist_ids = [(5, 0, 0)]

        if not self.comissao_list:
            return {
                'domain': {
                    'planilha_id': []
                }
            }

        planilhas = self.comissao_list.planilha_ids

        domain = {
            'planilha_id': [
                ('id', 'in', planilhas.ids)
            ]
        }

        # 🔥 OPCIONAL: auto-selecionar a primeira planilha
        if len(planilhas) == 1:
            self.planilha_id = planilhas[0].id

        return {'domain': domain}

    @api.onchange('planilha_id')
    def _onchange_planilha_id(self):

        self.custom_checklist_ids = [(5, 0, 0)]

        if not self.planilha_id:
            return

        linhas = []

        for comp in self.planilha_id.competencia_ids:
            linhas.append((0, 0, {
                'name': comp.name,
                'description': comp.description,
                'peso': comp.peso,
                'escala': comp.escala,
                'competencia': comp.competencia_list.name,
            }))

        self.custom_checklist_ids = linhas

    @api.onchange('cargo_avaliador')
    def _onchange_cargo_avaliador(self):
        if self.cargo_avaliador:
            return {'domain': {'avaliador': [('job_id.id', '=', self.cargo_avaliador.id)]}}
        else:
            return {'domain': {'avaliador': []}}
    @api.onchange('cargo')
    def _onchange_cargo(self):
        if self.cargo:
            return {'domain': {'name': [('job_id.id', '=', self.cargo.id)]}}
        else:
            return {'domain': {'name': []}}

    @api.model
    def create_comissao_for_employee(self):
        employees_without_comissao = self.env['hr.employee'].sudo().search(
            [('id', 'not in', self.env['avaliar.funcionario'].mapped('name.id'))])
        for employee in employees_without_comissao:
            comissao_template_id = self.env['comissao.avaliadora'].search([], limit=1)  # Assuming you have a comissao.avaliadora to assign
            if comissao_template_id:
                self.env['avaliar.funcionario'].create({
                    'name': employee.id,
                    'cargo': employee.job_id.id,
                    'departamento': employee.department_id.id,
                    'comissao_list': [(4, comissao_template_id.id)],
                })

    def action_send(self):
        for rec in self:
            rec.write({
                'status': 'espera',
                'assinatura_colaborador': rec.name.sudo().name,
            })

        return True
    def action_cancelar(self):
        self.write({'status': 'cancelar'})

    def action_aprove(self):
        for record in self:
            record.refresh()
            if not record.exists():
                raise UserError("O registro não existe ou foi excluído.")

            if record.status != 'espera':
                raise UserError("A transição de estado é permitida apenas de 'Em espera' para 'Aprovado'.")
            record.write({'status': 'aprovar',
                          'assinatura_avaliador': record.avaliador.sudo().name
                          })
    def action_concluir(self):
        self.write({'status': 'concluir'})

    def action_rejeitar(self):

        self.write({'status': 'rejeitar'})



class PlanilhaAvaliacao(models.Model):
    _name = 'planilha.avaliacao'
    _description = 'Planilha de Avaliação'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nome da Planilha',
        required=True, tracking=True)
    #
    descricao = fields.Text(
        string='Descrição', tracking=True)

    competencia_ids = fields.Many2many(
        'avaliacaodesempenho.avaliacaodesempenho',
        'planilha_competencia_rel',
        'planilha_id',
        'competencia_id',
        string='Competências',
        required=True,
        tracking = True)

    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True , tracking=True)
