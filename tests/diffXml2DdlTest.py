import findDmlChanges

aFindChanges = findDmlChanges.FindChanges()


def doTests():
    tests = [
        ('postgres', 'Add table', 'empty.xml', 'schema1.xml',
            ('CREATE TABLE table1 (\n\tcol1 integer,\n\tcol2 integer\n)',)),
        ('postgres', 'Drop table', 'schema1.xml', 'empty.xml',
            ('DROP TABLE table1',)),
        ('postgres', 'Add a column last', 'schema1.xml', 'schema-add-column.xml', 
            ('ALTER TABLE table1 ADD col3 integer',)),
        ('postgres', 'Add a column first', 'schema1.xml', 'schema-add-column-1st.xml', 
            ('ALTER TABLE table1 ADD col0 integer',)),
        ('postgres', 'Add a column middle', 'schema1.xml', 'schema-add-column-middle.xml', 
            ('ALTER TABLE table1 ADD col1_5 integer',)),
        ('postgres', 'Add a column larger size', 'schema1.xml', 'schema-alter-column-larger.xml', 
            ('ALTER TABLE table1 ALTER col1 TYPE integer',)),
        ('postgres', 'Add a column smaller size', 'schema1.xml', 'schema-alter-column-smaller.xml', 
            ('ALTER TABLE table1 ALTER col1 TYPE integer',)),
        ('postgres', 'Rename a column', 'schema1.xml', 'schema-rename-column.xml', 
            ('ALTER TABLE table1 RENAME col2 TO col-newname',)),
        ('postgres', 'Drop column first', 'schema1.xml', 'schema-drop-column-first.xml', 
            ('ALTER TABLE table1 DROP col1',)),
        ('postgres', 'Drop column last', 'schema1.xml', 'schema-drop-column-last.xml', 
            ('ALTER TABLE table1 DROP col2',)),
        ('postgres', 'Drop column last', 'schema1.xml', 'schema-drop-column-last.xml', 
            ('ALTER TABLE table1 DROP col2',)),
        ('postgres', 'Rename Table', 'schema1.xml', 'schema-rename-table.xml', 
            ('ALTER TABLE table1 RENAME TO new_table_name',)),
        ('postgres', 'Change a table description', 'schema1.xml', 'schema-table-desc.xml', 
            ("COMMENT ON TABLE table1 IS 'A description'",)),
        ('postgres', 'Change a column table description', 'schema1.xml', 'schema-column-desc.xml', 
            ("COMMENT ON COLUMN table1.col1 IS 'A description'",)),
        
        # With constraints on firebird
        ('firebird', 'Rename a column', 'schema2.xml', 'schema2-rename-column.xml', 
            (
            'ALTER TABLE table2 DROP CONSTRAINT fk_fk_table1',
            'ALTER TABLE table1 DROP CONSTRAINT pk_table1',
            'ALTER TABLE table1 ALTER id TO table1_id',
            'ALTER TABLE table1 ADD CONSTRAINT pk_table1 PRIMARY KEY (table1_id)',
            'ALTER TABLE table2 ADD CONSTRAINT fk_fk_table1 FOREIGN KEY (fk_table1) REFERENCES table1(table1_id)',
            )
        ),
    ]
    for test in tests:
        aFindChanges.setDbms(test[0])
        rets = aFindChanges.diffFiles('tests/' + test[2], 'tests/' + test[3])
        for nIndex, ret in enumerate(rets):
            if len(test[4]) > nIndex and ret[1] != test[4][nIndex]:
                print test[1]
                print 'Should be "%s" instead of "%s"' % (test[4][nIndex], ret[1])
            elif len(test[4]) < nIndex + 1:
                print test[1]
                print 'Extra command "%s"' % (ret[1])
    
if __name__ == "__main__":
    doTests()