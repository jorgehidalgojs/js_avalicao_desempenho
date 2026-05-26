
from odoo import models, fields, api,  exceptions
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class AvaliacaoDashboard(models.Model):
    _name = 'avaliacao.dashboard'
    _description = 'Dashboard de Avaliações'

    total_novas = fields.Integer(string='Total de Novas Avaliações')
    total_a_serem_avaliadas = fields.Integer(string='Total de Avaliações a Serem Avaliadas')
    total_canceladas = fields.Integer(string='Total de Avaliações Canceladas')


class avaliacaodesempenho(models.Model):
    _name = 'avaliacaodesempenho.avaliacaodesempenho'
    _description = 'avaliacaodesempenho.avaliacaodesempenho'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Descricao', required=True, tracking=True)
    peso = fields.Float(string='Peso',tracking=True)
    escala = fields.Float(string='Escala', required=True, default=10.0,tracking=True)
    # competencia = fields.Char(string="Competencia")
    competencia_list = fields.Many2one('avaliar.template', string="Tipo de competência", required=True,tracking=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True, tracking=True)

class ComissaAvaliadora(models.Model):
    _name = 'comissao.avaliadora'
    _description = 'Comissao Valiadora'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True,tracking=True)
    funcionario_ids = fields.Many2many('hr.employee', string='Funcionários',relation='comissao_avaliadora_funcionario_rel', required=True,tracking=True)
    cargo = fields.Many2one(related='funcionario_ids.job_id', related_sudo=True, string='Cargo', store=True,tracking=True)
    departamento_ids = fields.Many2many('hr.department', string='Departamentos', required=True,tracking=True)
    avaliador_ids = fields.Many2many('hr.employee', string='Avaliadores', relation='comissao_avaliadora_avaliador_rel', required=True,tracking=True)
    competencia_list = fields.Many2many('avaliacaodesempenho.avaliacaodesempenho', 'avaliar_comissao_rel', string="Tipo de competência", required =True,tracking=True)
    planilha_ids = fields.Many2many('planilha.avaliacao','comissao_planilha_rel','comissao_id','planilha_id',string='Planilhas de Avaliação',required=True,tracking=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    @api.onchange('departamento_ids')
    def _onchange_departamento_ids(self):
        if self.departamento_ids:
            domain = [('department_id', 'in', self.departamento_ids.ids)]
            return {'domain': {'funcionario_ids': domain}}
        return {'domain': {'funcionario_ids': []}}

    @api.depends('funcionario_ids')
    def _compute_cargos(self):
        for record in self:
            record.cargo_ids = [(6, 0, record.funcionario_ids.sudo().mapped('job_id').ids)]

    def remove_funcionario(self, employee_id):
        self.ensure_one()
        if employee_id in self.funcionario_ids.ids:
            self.write({
                'funcionario_ids': [(3, employee_id)]
            })

    @api.onchange('departamento_ids')
    def _onchange_departamento_ids(self):
        domain = [('department_id', 'in', self.departamento_ids.ids)]
        funcionarios = self.env['hr.employee'].sudo().search(domain)
        self.funcionario_ids = [(6, 0, funcionarios.ids)]


    @api.onchange('departamento_ids')
    def _onchange_departamento_ids(self):
        domain = [('department_id', 'in', self.departamento_ids.ids)]
        funcionarios = self.env['hr.employee'].sudo().search(domain)
        self.funcionario_ids = [(6, 0, funcionarios.ids)]
    def remove_funcionario(self, employee_id):
        self.ensure_one()

class AvaliacaoType(models.Model):
    _name = 'avaliacao.tipo'
    _description = 'Tipo de Avaliacao'

    name = fields.Char(string='Name', required=True)
    description = fields.Html(string='Descricao')
    peso = fields.Float(string='Peso')
    escala = fields.Float(string='Escala', required=True, default=10.0)
    nota = fields.Float(string="Nota Atribuida")
    competencia = fields.Char(string="Competencia")
    trimestre1 = fields.Char(string="1º Trimestre")
    trimestre2 = fields.Char(string="2º Trimestre")
    trimestre3 = fields.Char(string="3º Trimestre")
    trimestre4 = fields.Char(string="4º Trimestre")
    funcionario_id = fields.Many2one('avaliar.funcionario', string='Funcionario', ondelete='cascade')
    individual_id = fields.Many2one('avaliacao.individual', string='Funcionario', ondelete='cascade')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    color_nota = fields.Char(compute='_compute_color_nota')
    @api.model
    def create(self, vals):
        if vals.get('trimestre2') or vals.get('trimestre3') or vals.get('trimestre4'):
            raise exceptions.ValidationError("Você não pode preencher Trimestres posteriores durante a criação.")
        return super(AvaliacaoType, self).create(vals)

    def write(self, vals):
        for record in self:
            if 'trimestre1' in vals:
                if record.trimestre2 or record.trimestre3 or record.trimestre4:
                    raise exceptions.ValidationError(
                        "Não é permitido editar Trimestre 1 após o preenchimento de trimestres subsequentes.")
            if 'trimestre2' in vals:
                if record.trimestre3 or record.trimestre4:
                    raise exceptions.ValidationError(
                        "Não é permitido editar Trimestre 2 após o preenchimento dos trimestres subsequentes.")
            if 'trimestre3' in vals:
                if record.trimestre4:
                    raise exceptions.ValidationError(
                        "Não é permitido editar Trimestre 3 após o preenchimento do Trimestre 4.")
        return super(AvaliacaoType, self).write(vals)

    @api.constrains('nota', 'escala')
    def _check_nota_escala(self):
        for avaliacao in self:
            if avaliacao.nota > avaliacao.escala:
                raise ValidationError(
                    "A nota não pode ser maior que a escala."
                )

    @api.onchange('nota', 'escala')
    def _onchange_nota_escala(self):
        if self.nota > float(self.escala):
            return {
                'warning': {
                    'title': "Nota Inválida",
                    'message': "A nota não pode ser maior que a escala. Verifique e ajuste a nota."
                }
            }

    @api.depends('nota', 'escala')
    def _compute_color_nota(self):

        for record in self:

            if record.nota > record.escala:
                record.color_nota = 'red'
            else:
                record.color_nota = 'black'


