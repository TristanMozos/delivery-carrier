<?php
//**********************************************************
// AUTHOR..........: ALBERT ROIG.
// CREATION DATA...: 06/03/2017.
// NOTES...........: Example of obtaining the label.
//**********************************************************
?>

<form action="GLS_B2B_EtiquetaEnvio(Label_Impressor_PHP).php" method="get">
<br><b>INTRODUZCA ESTA INFORMACIÓN:</b><br><br>
Referencia....: <input type="text" name="Referencia" size="40" value=""> ............... (La referencia del cliente)<br><br>
Tipo Etiqueta: <select name="Tipo">
	<option value="PDF">PDF</option>
	<option value="JPG">JPG</option>
	<option value="PNG">PNG</option>
	<option value="EPL">EPL</option>
	<option value="DPL">DPL</option>
	<option value="XML">XML</option>
</select>
<br><br>
<input type="submit" value="Submit">
</form>

<?php

$url = "https://wsclientes.asmred.com/b2b.asmx";

// FUNCIONA SOLO CON ENVIOS NO ENTREGADOS.
// XML NO RETORNA NADA.

$Referencia = $_GET['Referencia'];
$Tipo       = $_GET['Tipo'];

// Ahora podemos obtener la etiqueta codificada en base64
$XML='<?xml version="1.0" encoding="utf-8"?>
	<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
	<soap12:Body>
	<EtiquetaEnvio xmlns="http://www.asmred.com/">
		<codigo>'.$Referencia.'</codigo>
		<tipoEtiqueta>'.strtoupper($Tipo).'</tipoEtiqueta>
	</EtiquetaEnvio>
	</soap12:Body>
	</soap12:Envelope>';

//echo "<br>WS PETICION DE ETIQUETA<br>".$XML."<br>";

$ch = curl_init();

curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, FALSE);
curl_setopt($ch, CURLOPT_HEADER, FALSE);
curl_setopt($ch, CURLOPT_FORBID_REUSE, TRUE);
curl_setopt($ch, CURLOPT_FRESH_CONNECT, TRUE);
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_POSTFIELDS, $XML);
curl_setopt($ch, CURLOPT_HTTPHEADER, Array("Content-Type: text/xml; charset=UTF-8"));

$postResult = curl_exec($ch);

if (curl_errno($ch)) {
	echo 'No se pudo llamar al WS de GLS<br>';
}

$result = strpos($postResult, '<base64Binary>');

if($result == false){
	echo '<font size="5">No se ha retornado ninguna etiqueta.</font>';
}
else {
	if	(strtoupper($Tipo) == "PDF") $Extension = ".pdf";
	else if (strtoupper($Tipo) == "JPG") $Extension = ".jpg";
	else if (strtoupper($Tipo) == "PNG") $Extension = ".png";
	else if (strtoupper($Tipo) == "EPL") $Extension = ".epl.txt";
	else if (strtoupper($Tipo) == "DPL") $Extension = ".dpl.txt";
	else if (strtoupper($Tipo) == "XML") $Extension = ".xml";

	$xml = simplexml_load_string($postResult, NULL, NULL, "http://http://www.w3.org/2003/05/soap-envelope");
	$xml->registerXPathNamespace("asm","http://www.asmred.com/");
	$arr = $xml->xpath("//asm:EtiquetaEnvioResponse/asm:EtiquetaEnvioResult/asm:base64Binary");

	$Tot = sizeof($arr);

        for( $Num=0 ; $Num <= sizeof($arr)-1 ; $Num++ ) {
		
		$descodificar = base64_decode($arr[$Num]);

		$NumBul = $Num + 1;

		if ($Extension == ".jpg" or $Extension == ".png") 
			$Nombre = 'GLS_etiqueta_' . $Referencia . ' (' . $NumBul . ' de ' . $Tot . ')' . $Extension;
		else
			$Nombre = 'GLS_etiqueta_' . $Referencia . $Extension;
		
		if(!$fp2 = fopen($Nombre,"wb+")){
			echo 'IMPOSIBLE ABRIR EL ARCHIVO $Nombre <br>';
		}

		if(!fwrite($fp2, trim($descodificar))){
			echo'IMPOSIBLE escribir EL ARCHIVO $Nombre <br>';
		}
		fclose($fp2);

		echo 'Etiqueta generada en fichero: ' . $Nombre . '<br>';
	}
}

/*
$xslDoc = new DOMDocument();
$xslDoc->load("http://iconnection.tnt.com:81/Shipper/NewStyleSheets/label.xsl");

$xmlDoc = new DOMDocument();
$xmlDoc->load("etiqueta_GE370586679ES.xml");

$proc = new XSLTProcessor();

$proc->importStylesheet($xslDoc);
//echo 'hola3';

echo $proc->transformToXML($xmlDoc);
*/
/*
$xml = new DOMDocument;
$xml->load('etiqueta_GE370586679ES.xml');

$xsl = new DOMDocument;
$xsl->load('http://iconnection.tnt.com:81/Shipper/NewStyleSheets/label.xsl');

// Configure the transformer
$proc = new XSLTProcessor;
$proc->importStyleSheet($xsl); // attach the xsl rules

$proc->transformToURI($xml, 'file:///C:/wamp/www/php_mios/out.html');
echo 'hola';
echo file_get_contents('out.html');
*/
/*
$XML = new DOMDocument();
//$XML->load('messages.xml');
$XML->load('etiqueta_GE370586679ES.xml');

# START XSLT
$xslt = new XSLTProcessor();
$XSL = new DOMDocument();
//$XSL->load('msg.xsl');
$XSL->load('label.xsl');
$xslt->importStylesheet( $XSL );
header('Content-Type: application/xml');
print $xslt->transformToXML( $XML );
*/

?>